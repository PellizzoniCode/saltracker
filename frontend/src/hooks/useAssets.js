import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client.js";

export function useAssets() {
  const [assets, setAssets] = useState([]);
  const [nextToken, setNextToken] = useState(null);
  const [message, setMessage] = useState("");
  const [query, setQuery] = useState("");

  const loadAssets = useCallback(async ({
    append = false,
    token = null,
  } = {}) => {
    try {
      const params = new URLSearchParams();

      if (query) {
        params.set("q", query);
      }

      if (token) {
        params.set("nextToken", token);
      }

      const queryString = params.toString();
      const result = await api(
        `/assets${queryString ? `?${queryString}` : ""}`
      );

      setAssets((current) =>
        append ? [...current, ...result.items] : result.items
      );
      setNextToken(result.nextToken || null);
      setMessage("");
    } catch (error) {
      setMessage(error.message);
    }
  }, [query]);

  useEffect(() => {
    loadAssets();
  }, [loadAssets]);

  return {
    assets,
    nextToken,
    message,
    setMessage,
    query,
    setQuery,
    loadAssets,
  };
}
