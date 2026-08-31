import { createFileRoute, redirect } from "@tanstack/react-router";
import { Clock } from "lucide-react";

import { StorageFileListPage } from "@/components/storage-intelligence/file-list-page";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/storage-intelligence/old-files")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: () => (
    <StorageFileListPage
      title="Old files"
      description="Files that haven't been modified in a long time, oldest first."
      apiPath="/v1/storage/old-files"
      emptyIcon={Clock}
      emptyTitle="No old files found"
      emptyDescription="Run a storage analysis to check for files that haven't been modified recently."
      dateLabel="Modified"
      getDate={(file) => file.provider_modified_at}
    />
  ),
});
