import { PageShell } from "@/components/PageShell";

const errors: Record<string, string> = {
  invalid: "The administrator credential was not accepted.",
  required: "Enter an administrator credential to continue.",
  unavailable: "Administrator authentication is temporarily unavailable."
};

export default async function AdminLoginPage({
  searchParams
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;
  return (
    <PageShell
      title="Admin sign in"
      eyebrow="Restricted area"
      description="Authenticate with an administrator credential to manage pipeline operations."
    >
      <form action="/admin/session" className="form-panel" method="post">
        <label>
          <span>Administrator credential</span>
          <input autoComplete="current-password" name="token" required type="password" />
        </label>
        {error && errors[error] ? <p className="state-panel error-state" role="alert">{errors[error]}</p> : null}
        <button className="primary-button" type="submit">Sign in</button>
      </form>
    </PageShell>
  );
}
