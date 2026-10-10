import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client.js";

export function useAssetGallery(assets) {
  const [galleryItems, setGalleryItems] = useState([]);
  const [galleryLoading, setGalleryLoading] = useState(false);
  const [galleryMessage, setGalleryMessage] = useState("");

  const loadGallery = useCallback(async () => {
    const photoAssets = assets.filter((asset) => asset.imageKey);

    if (!photoAssets.length) {
      setGalleryItems([]);
      setGalleryMessage("");
      return;
    }

    setGalleryLoading(true);
    setGalleryMessage("");

    const results = await Promise.allSettled(
      photoAssets.map(async (asset) => {
        const photoDetails = await api(
          `/assets/${encodeURIComponent(asset.assetId)}/photo`
        );

        return {
          ...asset,
          ...photoDetails,
        };
      })
    );

    const visibleItems = results
      .filter((result) => result.status === "fulfilled")
      .map((result) => result.value);

    const failedCount =
      results.length - visibleItems.length;

    setGalleryItems(visibleItems);

    if (failedCount) {
      setGalleryMessage(
        `${failedCount} photograph${
          failedCount === 1 ? "" : "s"
        } could not be loaded. Refresh the gallery to try again.`
      );
    }

    setGalleryLoading(false);
  }, [assets]);

  useEffect(() => {
    loadGallery();
  }, [loadGallery]);

  return { galleryItems, galleryLoading, galleryMessage, loadGallery };
}
