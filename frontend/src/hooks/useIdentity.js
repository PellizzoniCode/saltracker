import { useEffect, useState } from "react";
import { fetchAuthSession } from "aws-amplify/auth";

// Mirrors the backend rules so the UI only offers actions the API will
// allow. The API remains the authority.
export function useIdentity() {
  const [identity, setIdentity] = useState(null);

  useEffect(() => {
    let active = true;

    fetchAuthSession()
      .then((session) => {
        const payload = session.tokens?.idToken?.payload || {};

        if (active) {
          setIdentity({
            sub: payload.sub,
            groups: new Set(payload["cognito:groups"] || []),
            department: payload["custom:department"],
          });
        }
      })
      .catch(() => {
        if (active) setIdentity(null);
      });

    return () => {
      active = false;
    };
  }, []);

  return identity;
}
