import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client.js";
import { emptyMaintenance } from "../constants/maintenance.js";
import { useIdentity } from "./useIdentity.js";

export function useMaintenance(asset) {
  const [history, setHistory] = useState([]);
  const [schedule, setSchedule] = useState(null);
  const [aiRecommendation, setAiRecommendation] =
    useState(null);
  const [maintenanceForm, setMaintenanceForm] =
    useState(emptyMaintenance);
  const [loading, setLoading] = useState(true);
  const [savingMaintenance, setSavingMaintenance] =
    useState(false);
  const [generatingAi, setGeneratingAi] =
    useState(false);
  const [maintenanceMessage, setMaintenanceMessage] =
    useState("");
  const [editingMaintenance, setEditingMaintenance] =
    useState(null);
  const editingMaintenanceId =
    editingMaintenance?.maintenanceId ?? null;
  const identity = useIdentity();
  const isAdministrator =
    identity?.groups.has("Administrator") ?? false;

  function canEditMaintenance(item) {
    if (isAdministrator) return true;

    return Boolean(
      identity?.groups.has("Technician") &&
        identity.sub &&
        item.performedBy === identity.sub &&
        identity.department &&
        identity.department === asset.department
    );
  }

  const showMaintenanceActions =
    isAdministrator || history.some(canEditMaintenance);

  const loadMaintenance = useCallback(async () => {
    setLoading(true);

    try {
      const result = await api(
        `/assets/${encodeURIComponent(
          asset.assetId
        )}/maintenance`
      );

      setHistory(result.items || []);
      setSchedule(result.recommendation || null);
      setMaintenanceMessage("");
    } catch (error) {
      setMaintenanceMessage(error.message);
    } finally {
      setLoading(false);
    }
  }, [asset.assetId]);

  useEffect(() => {
    loadMaintenance();
  }, [loadMaintenance]);

  function updateMaintenanceField(event) {
    const { name, value } = event.target;

    setMaintenanceForm((current) => ({
      ...current,
      [name]: value,
    }));
  }

  function maintenancePath(maintenanceId) {
    const base = `/assets/${encodeURIComponent(
      asset.assetId
    )}/maintenance`;

    return maintenanceId
      ? `${base}/${encodeURIComponent(maintenanceId)}`
      : base;
  }

  function editMaintenance(item) {
    setEditingMaintenance(item);
    setMaintenanceForm(
      Object.fromEntries(
        Object.keys(emptyMaintenance).map((key) => [
          key,
          item[key] ?? "",
        ])
      )
    );
    setMaintenanceMessage("");
  }

  function cancelEditMaintenance() {
    setEditingMaintenance(null);
    setMaintenanceForm(emptyMaintenance);
  }

  async function deleteMaintenance(item) {
    if (
      !window.confirm(
        `Delete the ${item.maintenanceType} record from ${item.performedDate}?`
      )
    ) {
      return;
    }

    setMaintenanceMessage("");

    try {
      const result = await api(
        maintenancePath(item.maintenanceId),
        { method: "DELETE" }
      );

      if (editingMaintenanceId === item.maintenanceId) {
        cancelEditMaintenance();
      }

      setMaintenanceMessage(result.message);
      await loadMaintenance();
    } catch (error) {
      setMaintenanceMessage(error.message);
    }
  }

  async function recordMaintenance(event) {
    event.preventDefault();

    if (savingMaintenance) return;

    setSavingMaintenance(true);
    setMaintenanceMessage("");

    try {
      const payload = Object.fromEntries(
        Object.entries(maintenanceForm).map(
          ([key, value]) => [
            key,
            value === "" ? null : value,
          ]
        )
      );

      if (editingMaintenance) {
        payload.expectedUpdatedAt =
          editingMaintenance.updatedAt ?? null;
      }

      const result = await api(
        maintenancePath(editingMaintenanceId),
        {
          method: editingMaintenanceId ? "PUT" : "POST",
          body: JSON.stringify(payload),
        }
      );

      setMaintenanceMessage(result.message);
      setMaintenanceForm(emptyMaintenance);
      setEditingMaintenance(null);
      setAiRecommendation(null);
      await loadMaintenance();
    } catch (error) {
      setMaintenanceMessage(error.message);
    } finally {
      setSavingMaintenance(false);
    }
  }

  async function generateAiRecommendation() {
    if (generatingAi) return;

    setGeneratingAi(true);
    setMaintenanceMessage("");

    try {
      const result = await api(
        `/assets/${encodeURIComponent(
          asset.assetId
        )}/maintenance-recommendation`,
        {
          method: "POST",
        }
      );

      setSchedule(result.schedule || null);
      setAiRecommendation(
        result.aiRecommendation || null
      );
      setMaintenanceMessage( "" );
    } catch (error) {
      setMaintenanceMessage(error.message);
    } finally {
      setGeneratingAi(false);
    }
  }

  return {
    history,
    schedule,
    aiRecommendation,
    maintenanceForm,
    loading,
    savingMaintenance,
    generatingAi,
    maintenanceMessage,
    editingMaintenanceId,
    isAdministrator,
    canEditMaintenance,
    showMaintenanceActions,
    loadMaintenance,
    updateMaintenanceField,
    editMaintenance,
    cancelEditMaintenance,
    deleteMaintenance,
    recordMaintenance,
    generateAiRecommendation,
  };
}
