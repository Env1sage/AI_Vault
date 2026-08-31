import { createFileRoute, redirect } from "@tanstack/react-router";
import { FileWarning } from "lucide-react";

import { StorageFileListPage } from "@/components/storage-intelligence/file-list-page";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/storage-intelligence/candidates")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: () => (
    <StorageFileListPage
      title="Potential temporary files"
      description="Files that look like scratch or temporary output (by name pattern and location), not confirmed duplicates."
      apiPath="/v1/storage/candidates"
      emptyIcon={FileWarning}
      emptyTitle="No temporary-file candidates found"
      emptyDescription="Run a storage analysis to check for likely temporary or scratch files."
      dateLabel="Modified"
      getDate={(file) => file.provider_modified_at}
    />
  ),
});
