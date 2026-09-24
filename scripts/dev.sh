#!/usr/bin/env bash
# One-stop helper for deploying and testing the dev stack.
#
#   scripts/dev.sh up                 test, build, deploy, write frontend/.env, seed sample data
#   scripts/dev.sh deploy             build + deploy only (skips tests)
#   scripts/dev.sh sync               watch backend code and hot-sync Lambda changes (sam sync)
#   scripts/dev.sh env                write frontend/.env from the stack outputs
#   scripts/dev.sh seed               load sample-data/assets.json through the deployed Lambda
#   scripts/dev.sh user -e EMAIL -p PASSWORD -g GROUP [-d DEPARTMENT]
#                                     create a confirmed Cognito user in GROUP
#                                     (omit -p to be prompted for the password)
#   scripts/dev.sh web                start the Vite dev server
#   scripts/dev.sh down [--purge]     delete the stack (--purge also deletes the retained table)
#
# Override defaults with STACK_NAME, AWS_REGION, ENVIRONMENT.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE="$ROOT/infrastructure/template.yaml"
ENVIRONMENT="${ENVIRONMENT:-dev}"
STACK_NAME="${STACK_NAME:-smart-asset-tracker-$ENVIRONMENT}"
export AWS_REGION="${AWS_REGION:-us-east-1}"
GROUPS_ALLOWED="Employee Technician Manager Administrator Auditor"

cd "$ROOT"

log() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
die() { printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; exit 1; }

require() {
  for cmd in "$@"; do
    command -v "$cmd" >/dev/null || die "'$cmd' is required but not installed."
  done
}

check_aws() {
  require aws sam
  aws sts get-caller-identity --query Account --output text >/dev/null 2>&1 \
    || die "AWS credentials are not configured (run 'aws configure' or 'aws sso login')."
}

output() {
  aws cloudformation describe-stacks --stack-name "$STACK_NAME" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text
}

cmd_test() {
  log "Running unit tests"
  python3 -m unittest discover -s backend/tests
}

cmd_build() {
  log "Validating template"
  sam validate --template-file "$TEMPLATE" --lint
  local build_args=(--template-file "$TEMPLATE" --cached --parallel)
  if ! command -v python3.11 >/dev/null; then
    log "python3.11 not found, building inside a container"
    build_args+=(--use-container)
  fi
  log "Building (cached)"
  sam build "${build_args[@]}"
}

cmd_deploy() {
  check_aws
  cmd_build
  log "Deploying $STACK_NAME to $AWS_REGION"
  sam deploy \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --resolve-s3 \
    --s3-prefix "$STACK_NAME" \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides "Environment=$ENVIRONMENT" \
    --no-confirm-changeset \
    --no-fail-on-empty-changeset
  cmd_env
}

cmd_sync() {
  check_aws
  log "Watching for changes (Ctrl+C to stop). Dev stacks only — this skips changesets."
  sam sync \
    --template-file "$TEMPLATE" \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides "Environment=$ENVIRONMENT" \
    --watch
}

cmd_env() {
  check_aws
  log "Writing frontend/.env from stack outputs"
  cat > frontend/.env <<EOF
VITE_AWS_REGION=$AWS_REGION
VITE_USER_POOL_ID=$(output UserPoolId)
VITE_USER_POOL_CLIENT_ID=$(output UserPoolClientId)
VITE_API_URL=$(output ApiUrl)
EOF
  cat frontend/.env
}

cmd_seed() {
  check_aws
  local fn="smart-asset-api-$ENVIRONMENT"
  log "Seeding sample assets through $fn"
  # Invoking the real handler with synthetic Administrator claims keeps
  # validation and the atomic tag reservation in play. Duplicates return 409.
  FN="$fn" python3 - <<'PY'
import json, os, subprocess, tempfile

with open("sample-data/assets.json") as f:
    assets = json.load(f)

for asset in assets:
    event = {
        "httpMethod": "POST",
        "body": json.dumps(asset),
        "requestContext": {"authorizer": {"claims": {
            "sub": "dev-seed-script", "cognito:groups": "Administrator"}}},
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as ev, \
         tempfile.NamedTemporaryFile(suffix=".json", delete=False) as out:
        json.dump(event, ev)
    subprocess.run(
        ["aws", "lambda", "invoke", "--function-name", os.environ["FN"],
         "--cli-binary-format", "raw-in-base64-out",
         "--payload", f"file://{ev.name}", out.name],
        check=True, stdout=subprocess.DEVNULL)
    with open(out.name) as f:
        result = json.load(f)
    os.unlink(ev.name); os.unlink(out.name)
    status = result.get("statusCode")
    note = {201: "created", 409: "already exists"}.get(status, result.get("body"))
    print(f"  {asset['assetTag']}: {status} {note}")
PY
}

cmd_user() {
  check_aws
  local usage="Usage: dev.sh user -e EMAIL -p PASSWORD -g GROUP [-d DEPARTMENT]"
  local email="" password="" group="" department=""
  while [[ $# -gt 0 ]]; do
    [[ $# -ge 2 ]] || die "Missing value for $1. $usage"
    case "$1" in
      -e|--email)      email="$2" ;;
      -p|--password)   password="$2" ;;
      -g|--group)      group="$2" ;;
      -d|--department) department="$2" ;;
      *) die "Unknown option '$1'. $usage" ;;
    esac
    shift 2
  done
  [[ -n "$email" && -n "$group" ]] || die "$usage"
  [[ " $GROUPS_ALLOWED " == *" $group "* ]] || die "GROUP must be one of: $GROUPS_ALLOWED"

  local pool
  pool="$(output UserPoolId 2>/dev/null || true)"
  [[ -n "$pool" && "$pool" != "None" ]] \
    || die "Stack $STACK_NAME not found in $AWS_REGION — run 'scripts/dev.sh deploy' first."

  if [[ -z "$password" ]]; then password="$(prompt_password)"; fi
  check_password "$password"

  local attrs=(Name=email,Value="$email" Name=email_verified,Value=true)
  [[ -n "$department" ]] && attrs+=(Name=custom:department,Value="$department")

  log "Creating $email in $group"
  if ! aws cognito-idp admin-get-user --user-pool-id "$pool" --username "$email" >/dev/null 2>&1; then
    aws cognito-idp admin-create-user --user-pool-id "$pool" --username "$email" \
      --user-attributes "${attrs[@]}" --message-action SUPPRESS >/dev/null
  elif [[ -n "$department" ]]; then
    aws cognito-idp admin-update-user-attributes --user-pool-id "$pool" --username "$email" \
      --user-attributes Name=custom:department,Value="$department"
  fi
  aws cognito-idp admin-set-user-password --user-pool-id "$pool" --username "$email" \
    --password "$password" --permanent
  aws cognito-idp admin-add-user-to-group --user-pool-id "$pool" --username "$email" \
    --group-name "$group"

  local sub
  sub="$(aws cognito-idp admin-get-user --user-pool-id "$pool" --username "$email" \
    --query "UserAttributes[?Name=='sub'].Value" --output text)"
  printf '  email: %s\n  group: %s\n  sub:   %s\n' "$email" "$group" "$sub"
}

# Prompts twice without echoing, for when the password should stay out of shell history.
prompt_password() {
  local password confirm
  [[ -t 0 ]] || die "No terminal to prompt on — pass the password with -p."
  read -rsp "Password: " password; echo >&2
  read -rsp "Confirm password: " confirm; echo >&2
  [[ "$password" == "$confirm" ]] || die "Passwords do not match."
  printf '%s' "$password"
}

# Mirrors the user pool's password policy so a bad password fails before calling Cognito.
check_password() {
  local password="$1"
  [[ ${#password} -ge 12 ]] || die "Password must be at least 12 characters."
  [[ "$password" =~ [[:lower:]] ]] || die "Password must contain a lowercase letter."
  [[ "$password" =~ [[:upper:]] ]] || die "Password must contain an uppercase letter."
  [[ "$password" =~ [[:digit:]] ]] || die "Password must contain a number."
  [[ "$password" =~ [^[:alnum:]] ]] || die "Password must contain a symbol."
  [[ "$password" != " "* && "$password" != *" " ]] || die "Password cannot start or end with a space."
}

cmd_web() {
  require npm
  [[ -f frontend/.env ]] || die "frontend/.env missing — run 'scripts/dev.sh env' first."
  cd frontend
  [[ -d node_modules ]] || npm ci
  npm run dev
}

cmd_down() {
  check_aws
  local table
  table="$(output AssetTableName 2>/dev/null || true)"
  log "Deleting stack $STACK_NAME"
  sam delete --stack-name "$STACK_NAME" --region "$AWS_REGION" --no-prompts
  if [[ "${1:-}" == "--purge" && -n "$table" && "$table" != "None" ]]; then
    log "Deleting retained table $table"
    aws dynamodb delete-table --table-name "$table" >/dev/null
  else
    log "Table ${table:-smart-asset-tracker-$ENVIRONMENT} was retained (use 'down --purge' to delete it)."
  fi
}

cmd_up() {
  cmd_test
  cmd_deploy
  cmd_seed
  log "Done. Create a login with: scripts/dev.sh user -e you@example.com -p 'Your-Pass123!' -g Administrator -d IT"
  log "Then start the UI with:     scripts/dev.sh web"
}

case "${1:-up}" in
  up)     cmd_up ;;
  test)   cmd_test ;;
  build)  cmd_build ;;
  deploy) cmd_deploy ;;
  sync)   cmd_sync ;;
  env)    cmd_env ;;
  seed)   cmd_seed ;;
  user)   shift; cmd_user "$@" ;;
  web)    cmd_web ;;
  down)   shift; cmd_down "$@" ;;
  -h|--help|help) sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//' ;;
  *)      die "Unknown command '$1'. Run 'scripts/dev.sh help'." ;;
esac
