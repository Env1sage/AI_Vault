import { createFileRoute, redirect } from "@tanstack/react-router";
import { Eye } from "lucide-react";

import { StorageFileListPage } from "@/components/storage-intelligence/file-list-page";
import { useAuthStore } from "@/stores/auth-store";

export const Route = createFileRoute("/storage-intelligence/inactive-files")({
  beforeLoad: () => {
    if (useAuthStore.getState().status !== "authenticated") {
      throw redirect({ to: "/login" });
    }
  },
  component: () => (
    <StorageFileListPage
      title="Inactive files"
      description="Files nobody has opened in a long time, least recently viewed first."
      apiPath="/v1/storage/inactive-files"
      emptyIcon={Eye}
      emptyTitle="No inactive files found"
      emptyDescription="Run a storage analysis to check for files nobody has opened recently."
      dateLabel="Last opened"
      getDate={(file) => file.provider_viewed_at}
    />
  ),
});
