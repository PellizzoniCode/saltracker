import { fetchAuthSession } from "aws-amplify/auth";

const API_URL = import.meta.env.VITE_API_URL;

export async function api(path, options = {}) {
  const session = await fetchAuthSession();
  const token = session.tokens?.idToken?.toString();
  const result = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", Authorization: token, ...options.headers },
  });
  const body = await result.json();
  if (!result.ok) throw new Error(body.message || "Request failed");
  return body;
}
