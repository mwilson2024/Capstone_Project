import { Directory, File, Paths } from "expo-file-system";
import * as Sharing from "expo-sharing";

export async function downloadPhoto(photoUrl: string, fileName: string) {
  const directory = new Directory(Paths.cache, "event-photos");
  directory.create({ idempotent: true, intermediates: true });

  const destination = new File(
    directory,
    `${Date.now()}-${fileName.replace(/[^a-zA-Z0-9._-]/g, "_")}`
  );
  const downloaded = await File.downloadFileAsync(photoUrl, destination);

  if (!(await Sharing.isAvailableAsync())) {
    throw new Error("Saving photos is not available on this device.");
  }

  await Sharing.shareAsync(downloaded.uri, {
    mimeType: "image/*",
    UTI: "public.image",
    dialogTitle: "Save or share photo",
  });
}
