import { Notice } from "../../components/Notice.jsx";
import { PageHeader } from "../../components/PageHeader.jsx";
import { useMaintenance } from "../../hooks/useMaintenance.js";
import { AiRecommendationPanel } from "./AiRecommendationPanel.jsx";
import { AssetSummaryPanel } from "./AssetSummaryPanel.jsx";
import { DepreciationPanel } from "./DepreciationPanel.jsx";
import { MaintenanceForm } from "./MaintenanceForm.jsx";
import { MaintenanceHistoryTable } from "./MaintenanceHistoryTable.jsx";
import { SchedulePanel } from "./SchedulePanel.jsx";

export function MaintenancePage({
  asset,
  onBack,
  signOut,
  user,
}) {
  const {
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
  } = useMaintenance(asset);

  return (
    <main>
      <PageHeader
        eyebrow="MAINTENANCE INTELLIGENCE"
        title="Maintenance history and recommendations"
        user={user}
      >
        <div className="header-actions">
          <button
            type="button"
            className="secondary"
            onClick={onBack}
          >
            Back to inventory
          </button>

          <button
            type="button"
            className="secondary"
            onClick={signOut}
          >
            Sign out
          </button>
        </div>
      </PageHeader>

      {maintenanceMessage && (
        <Notice>{maintenanceMessage}</Notice>
      )}

      <AssetSummaryPanel asset={asset} />

      <DepreciationPanel depreciation={asset.depreciation} />

      <section className="maintenance-grid">
        <SchedulePanel schedule={schedule} loading={loading} />

        <AiRecommendationPanel
          recommendation={aiRecommendation}
          generating={generatingAi}
          onGenerate={generateAiRecommendation}
        />
      </section>

      <MaintenanceForm
        form={maintenanceForm}
        editingId={editingMaintenanceId}
        saving={savingMaintenance}
        onChange={updateMaintenanceField}
        onSubmit={recordMaintenance}
        onCancel={cancelEditMaintenance}
      />

      <MaintenanceHistoryTable
        history={history}
        loading={loading}
        showActions={showMaintenanceActions}
        canEdit={canEditMaintenance}
        isAdministrator={isAdministrator}
        onEdit={editMaintenance}
        onDelete={deleteMaintenance}
        onRefresh={loadMaintenance}
      />
    </main>
  );
}
