import { SignIn } from "@clerk/nextjs";
import { PageShell } from "@/components/PageShell";

export default function AdminLoginPage() {
  return (
    <PageShell
      title="Admin sign in"
      eyebrow="Restricted area"
      description="Sign in to manage pipeline operations."
    >
      <SignIn forceRedirectUrl="/admin" />
    </PageShell>
  );
}
