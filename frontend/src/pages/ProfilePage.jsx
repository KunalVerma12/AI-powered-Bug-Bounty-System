import { ProfilePanel } from "../components/ProfilePanel";
import { SectionTitle } from "../components/ui/SectionTitle";

export function ProfilePage(props) {
  const { summary, currentUser } = props;
  return (
    <div className="space-y-4">
      <SectionTitle
        eyebrow="Profile"
        title={currentUser ? "Operator Workspace" : "Authentication"}
        description={
          currentUser
            ? "Profile identity, scan ownership, confidence, and security activity in one enterprise-grade workspace."
            : "Create an account or sign in to launch scans and see only your own results."
        }
      />
      <ProfilePanel {...props} summary={summary} currentUser={currentUser} />
    </div>
  );
}
