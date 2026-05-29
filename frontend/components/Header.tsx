export function Header() {
  return (
    <header className="header">
      <div className="header-title">
        <strong>FPL Application Shell</strong>
        <span>Ready for FastAPI-backed reports, analysis, and recommendations.</span>
      </div>
      <div className="header-status" aria-label="Backend connection status">
        Backend: not connected
      </div>
    </header>
  );
}
