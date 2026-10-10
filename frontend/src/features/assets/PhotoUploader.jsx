import { AnalysisSuggestions } from "./AnalysisSuggestions.jsx";

export function PhotoUploader({
  inputRef,
  photo,
  uploading,
  saving,
  photoMessage,
  analysisMessage,
  checkingAnalysis,
  analysis,
  onSelect,
  onUpload,
  onApply,
  onReject,
}) {
  return (
    <div className="photo-upload">
      <label htmlFor="asset-photo"><span>Asset photo (optional)</span></label>
      <input id="asset-photo" ref={inputRef} type="file" accept="image/jpeg,image/png" disabled={uploading || saving} onChange={onSelect} />
      <button type="button" className="secondary" disabled={!photo || uploading || saving} onClick={onUpload}>
        {uploading ? "Uploading..." : "Upload photo"}
      </button>
      {photoMessage && <p role="status">{photoMessage}</p>}
      {analysisMessage && (
        <p role="status">{analysisMessage}</p>
      )}

      {checkingAnalysis && (
        <p className="analysis-status">
          Analyzing photograph...
        </p>
      )}

      {analysis && (
        <AnalysisSuggestions
          analysis={analysis}
          onApply={onApply}
          onReject={onReject}
        />
      )}
    </div>
  );
}
