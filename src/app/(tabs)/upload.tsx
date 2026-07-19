import { Ionicons } from "@expo/vector-icons";
import * as ImagePicker from "expo-image-picker";
import { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Dimensions,
  FlatList,
  Image,
  Modal,
  Platform,
  Pressable,
  SafeAreaView,
  StatusBar,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { apiFetch, apiUpload } from "@/lib/api";
import { useAuth } from "@/lib/AuthContext";
import { useCurrentEvent } from "@/lib/CurrentEventContext";
import { ThemeColors } from "@/theme/colors";
import { useTheme } from "@/theme/ThemeContext";

const { width: SCREEN_WIDTH } = Dimensions.get("window");
const THUMB = (SCREEN_WIDTH - 56) / 3;

const MAX_PHOTOS = 20;

type PhotoMimeType =
  | "image/jpeg"
  | "image/png"
  | "image/gif"
  | "image/webp"
  | "image/heic"
  | "image/heif";

type PickedPhoto = {
  id: string;
  uri: string;
  name: string;
  mimeType: PhotoMimeType;
};
type EventOption = { event_id: number; name: string };
type UploadResponse = {
  uploaded: number;
  results?: Array<{ status?: string; error?: string }>;
};

const PHOTO_MIME_BY_EXTENSION: Record<string, PhotoMimeType> = {
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  png: "image/png",
  gif: "image/gif",
  webp: "image/webp",
  heic: "image/heic",
  heif: "image/heif",
};

const PHOTO_EXTENSION_BY_MIME: Record<PhotoMimeType, string> = {
  "image/jpeg": "jpg",
  "image/png": "png",
  "image/gif": "gif",
  "image/webp": "webp",
  "image/heic": "heic",
  "image/heif": "heif",
};

function getSupportedMimeType(
  mimeType: string | null | undefined,
  fileNameOrUri: string
): PhotoMimeType | null {
  if (
    mimeType === "image/jpeg" ||
    mimeType === "image/png" ||
    mimeType === "image/gif" ||
    mimeType === "image/webp" ||
    mimeType === "image/heic" ||
    mimeType === "image/heif"
  ) {
    return mimeType;
  }

  const extension = fileNameOrUri
    .split(/[?#]/, 1)[0]
    .split(".")
    .pop()
    ?.toLowerCase();
  return extension ? PHOTO_MIME_BY_EXTENSION[extension] ?? null : null;
}

export default function UploadScreen() {
  const { colors: c } = useTheme();
  const { loggedIn } = useAuth();
  const { eventId, eventName, setCurrentEvent } = useCurrentEvent();
  const s = useMemo(() => makeStyles(c), [c]);
  const [photos, setPhotos] = useState<PickedPhoto[]>([]);
  const [uploading, setUploading] = useState(false);
  const [done, setDone] = useState(false);
  const [securityConfirmed, setSecurityConfirmed] = useState(false);
  const [events, setEvents] = useState<EventOption[]>([]);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [eventsError, setEventsError] = useState<string | null>(null);
  const [eventsAttempt, setEventsAttempt] = useState(0);
  const [eventMenuOpen, setEventMenuOpen] = useState(false);

  useEffect(() => {
    if (!loggedIn) {
      setEvents([]);
      setEventsError(null);
      return;
    }

    const controller = new AbortController();
    setEventsLoading(true);
    setEventsError(null);

    apiFetch("/users/me/events", undefined, "GET", controller.signal)
      .then((res) => {
        setEvents(Array.isArray(res) ? res : res.events ?? []);
      })
      .catch((error: unknown) => {
        if (error instanceof Error && error.name === "AbortError") return;
        setEventsError(
          error instanceof Error ? error.message : "Could not load events."
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) setEventsLoading(false);
      });

    return () => controller.abort();
  }, [loggedIn, eventsAttempt]);

  const selectedEventName =
    events.find((event) => event.event_id === eventId)?.name ??
    eventName ??
    null;

  const isValidImage = (photo: PickedPhoto) =>
    getSupportedMimeType(photo.mimeType, photo.name) !== null;

  const validateUpload = () => {
    if (!loggedIn) {
      Alert.alert("Login Required", "Log in before uploading photos.");
      return false;
    }

    if (!eventId) {
      Alert.alert("No Event Selected", "Choose which event these photos belong to.");
      return false;
    }

    if (photos.length === 0) {
      Alert.alert("No Photos", "Please select at least one photo.");
      return false;
    }

    if (photos.length > MAX_PHOTOS) {
      Alert.alert("Too Many Photos", `You can only upload ${MAX_PHOTOS} photos at once.`);
      return false;
    }

    const invalidPhoto = photos.find((photo) => !isValidImage(photo));
    if (invalidPhoto) {
      Alert.alert(
        "Invalid File",
        "Only JPG, JPEG, PNG, GIF, WebP, HEIC, and HEIF images are allowed."
      );
      return false;
    }

    if (!securityConfirmed) {
      Alert.alert("Security Check", "Please confirm the security check before uploading.");
      return false;
    }

    return true;
  };

  const pickFromLibrary = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== "granted") {
      Alert.alert(
        "Permission Required",
        "Please allow access to your photo library to upload images."
      );
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsMultipleSelection: true,
      quality: 0.85,
      selectionLimit: MAX_PHOTOS,
    });

    if (!result.canceled) {
      const picked: PickedPhoto[] = result.assets.flatMap((asset, index) => {
        const mimeType = getSupportedMimeType(
          asset.mimeType,
          asset.fileName ?? asset.uri
        );
        if (!mimeType) return [];

        return [
          {
            id: `${Date.now()}-${index}`,
            uri: asset.uri,
            name:
              asset.fileName ??
              `photo_${Date.now()}_${index}.${PHOTO_EXTENSION_BY_MIME[mimeType]}`,
            mimeType,
          },
        ];
      });

      if (picked.length !== result.assets.length) {
        Alert.alert(
          "Unsupported Files",
          "Only JPG, JPEG, PNG, GIF, WebP, HEIC, and HEIF images were added."
        );
      }

      const combined = [...photos, ...picked].slice(0, MAX_PHOTOS);

      if (photos.length + picked.length > MAX_PHOTOS) {
        Alert.alert("Upload Limit", `Only ${MAX_PHOTOS} photos can be selected at once.`);
      }

      setPhotos(combined);
      setDone(false);
    }
  };

  const remove = (id: string) =>
    setPhotos((prev) => prev.filter((p) => p.id !== id));

  const clearAll = () =>
    Alert.alert("Clear All", "Remove all selected photos?", [
      { text: "Cancel", style: "cancel" },
      { text: "Clear", style: "destructive", onPress: () => setPhotos([]) },
    ]);

  const handleUpload = async () => {
    if (!validateUpload()) return;

    setUploading(true);
    try {
      const formData = new FormData();

      formData.append("eventID", String(eventId));

      photos.forEach((photo) => {
        formData.append("files", {
          uri: photo.uri,
          name: photo.name,
          type: photo.mimeType,
        } as any);
      });

      const result = await apiUpload<UploadResponse>("/upload/user", formData);
      if (result.uploaded < 1) {
        const reason = result.results?.find((item) => item.error)?.error;
        throw new Error(reason ?? "The server did not accept any photos.");
      }

      setDone(true);
      setPhotos([]);
      setSecurityConfirmed(false);

      Alert.alert(
        "Upload Complete",
        `${result.uploaded} photo${result.uploaded !== 1 ? "s" : ""} uploaded to ${
          selectedEventName ?? `event ${eventId}`
        }.`
      );
    } catch (error: any) {
      Alert.alert("Upload Failed", error.message ?? "Please try again.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <SafeAreaView style={s.safe}>
      <StatusBar barStyle={c.statusBar} />

      <View style={s.header}>
        <View>
          <Text style={s.eyebrow}>DEVICE LIBRARY</Text>
          <Text style={s.title}>Upload</Text>
        </View>
        {photos.length > 0 && (
          <TouchableOpacity style={s.trashBtn} onPress={clearAll}>
            <Ionicons name="trash-outline" size={18} color={c.danger} />
          </TouchableOpacity>
        )}
      </View>

      <Text style={s.subtitle}>
        {photos.length > 0
          ? `${photos.length} photo${photos.length !== 1 ? "s" : ""} selected`
          : "No photos selected"}
      </Text>

      <View style={s.eventBox}>
        <Text style={s.eventLabel}>UPLOAD TO EVENT</Text>
        <TouchableOpacity
          accessibilityLabel="Select an event"
          accessibilityRole="button"
          activeOpacity={0.8}
          disabled={eventsLoading || Boolean(eventsError)}
          onPress={() => setEventMenuOpen(true)}
          style={[
            s.eventSelect,
            eventId !== null && s.eventSelectChosen,
            (eventsLoading || Boolean(eventsError)) && s.eventSelectDisabled,
          ]}
        >
          <View style={s.eventSelectText}>
            <Text style={s.eventSelectTitle} numberOfLines={1}>
              {eventsLoading
                ? "Loading events..."
                : selectedEventName ?? "Select an event"}
            </Text>
            {!eventsLoading && (
              <Text style={s.eventSelectHint} numberOfLines={1}>
                {selectedEventName
                  ? `Event ${eventId}`
                  : events.length > 0
                    ? `${events.length} available`
                    : "No events available"}
              </Text>
            )}
          </View>
          {eventsLoading ? (
            <ActivityIndicator size="small" color={c.accent} />
          ) : (
            <Ionicons name="chevron-down" size={20} color={c.textMuted} />
          )}
        </TouchableOpacity>
        {eventsError && (
          <View style={s.eventErrorRow}>
            <Text style={s.eventErrorText}>{eventsError}</Text>
            <TouchableOpacity
              onPress={() => setEventsAttempt((attempt) => attempt + 1)}
            >
              <Text style={s.eventRetryText}>Try again</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>

      <Modal
        visible={eventMenuOpen}
        transparent
        animationType="fade"
        onRequestClose={() => setEventMenuOpen(false)}
      >
        <View style={s.eventMenuBackdrop}>
          <Pressable
            accessibilityLabel="Close event selector"
            style={StyleSheet.absoluteFill}
            onPress={() => setEventMenuOpen(false)}
          />
          <View style={s.eventMenu}>
            <View style={s.eventMenuHeader}>
              <View>
                <Text style={s.eventMenuEyebrow}>UPLOAD TO</Text>
                <Text style={s.eventMenuTitle}>Select an event</Text>
              </View>
              <TouchableOpacity
                accessibilityLabel="Close event selector"
                onPress={() => setEventMenuOpen(false)}
                style={s.eventMenuClose}
              >
                <Ionicons name="close" size={20} color={c.textBright} />
              </TouchableOpacity>
            </View>
            <FlatList
              data={events}
              keyExtractor={(item) => String(item.event_id)}
              style={s.eventMenuList}
              contentContainerStyle={s.eventMenuListContent}
              ListEmptyComponent={
                <View style={s.eventMenuEmpty}>
                  <Ionicons
                    name="calendar-outline"
                    size={32}
                    color={c.textFaint}
                  />
                  <Text style={s.eventMenuEmptyText}>
                    No events are available for this account.
                  </Text>
                </View>
              }
              renderItem={({ item }) => {
                const selected = item.event_id === eventId;
                return (
                  <TouchableOpacity
                    activeOpacity={0.8}
                    onPress={() => {
                      setCurrentEvent(item.event_id, item.name);
                      setEventMenuOpen(false);
                    }}
                    style={[
                      s.eventOption,
                      selected && s.eventOptionSelected,
                    ]}
                  >
                    <View style={s.eventOptionIcon}>
                      <Ionicons
                        name="calendar-outline"
                        size={20}
                        color={selected ? "#fff" : c.accent}
                      />
                    </View>
                    <View style={s.eventOptionText}>
                      <Text
                        numberOfLines={1}
                        style={[
                          s.eventOptionName,
                          selected && s.eventOptionNameSelected,
                        ]}
                      >
                        {item.name}
                      </Text>
                      <Text
                        style={[
                          s.eventOptionId,
                          selected && s.eventOptionIdSelected,
                        ]}
                      >
                        Event {item.event_id}
                      </Text>
                    </View>
                    {selected && (
                      <Ionicons
                        name="checkmark-circle"
                        size={22}
                        color="#fff"
                      />
                    )}
                  </TouchableOpacity>
                );
              }}
            />
          </View>
        </View>
      </Modal>

      <View style={s.securityBox}>
        <Ionicons name="shield-checkmark-outline" size={20} color={c.successText} />
        <View style={{ flex: 1 }}>
          <Text style={s.securityTitle}>Security Check</Text>
          <Text style={s.securityText}>
            JPG, PNG, GIF, WebP, HEIC, and HEIF files are allowed. Uploads are
            authenticated and added to the selected event.
          </Text>
        </View>
      </View>

      {photos.length === 0 ? (
        <View style={s.empty}>
          <TouchableOpacity
            style={s.dropZone}
            onPress={pickFromLibrary}
            activeOpacity={0.8}
          >
            <View style={s.iconRing}>
              <Ionicons name="images-outline" size={36} color={c.accent} />
            </View>
            <Text style={s.dropTitle}>Choose Photos</Text>
            <Text style={s.dropSub}>
              Tap to browse your device library{"\n"}Up to 20 photos at once
            </Text>
            <View style={s.selectBadge}>
              <Ionicons name="add" size={14} color="#fff" />
              <Text style={s.selectBadgeText}>SELECT</Text>
            </View>
          </TouchableOpacity>

          {done && (
            <View style={s.successBanner}>
              <Ionicons name="checkmark-circle" size={18} color={c.successText} />
              <Text style={s.successText}>Photos uploaded successfully</Text>
            </View>
          )}
        </View>
      ) : (
        <FlatList
          data={photos}
          numColumns={3}
          keyExtractor={(item) => item.id}
          contentContainerStyle={s.grid}
          columnWrapperStyle={s.gridRow}
          showsVerticalScrollIndicator={false}
          renderItem={({ item }) => (
            <View style={[s.thumb, { width: THUMB, height: THUMB }]}>
              <Image
                source={{ uri: item.uri }}
                style={s.thumbImg}
                resizeMode="cover"
              />
              <TouchableOpacity
                style={s.removeBtn}
                onPress={() => remove(item.id)}
                hitSlop={{ top: 8, left: 8, bottom: 8, right: 8 }}
              >
                <Ionicons name="close-circle" size={22} color={c.danger} />
              </TouchableOpacity>
            </View>
          )}
          ListFooterComponent={
            <TouchableOpacity
              style={s.addMore}
              onPress={pickFromLibrary}
              activeOpacity={0.8}
            >
              <Ionicons name="add" size={20} color={c.accent} />
              <Text style={s.addMoreText}>Add More</Text>
            </TouchableOpacity>
          }
        />
      )}

      {photos.length > 0 && (
        <View style={s.footer}>
          <TouchableOpacity
            style={s.confirmRow}
            onPress={() => setSecurityConfirmed(!securityConfirmed)}
            activeOpacity={0.8}
          >
            <Ionicons
              name={securityConfirmed ? "checkbox" : "square-outline"}
              size={22}
              color={securityConfirmed ? c.successText : c.textMuted}
            />
            <Text style={s.confirmText}>
              I confirm these photos are safe to upload.
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[
              s.uploadBtn,
              uploading && s.uploadBtnBusy,
              !securityConfirmed && s.uploadBtnDisabled,
            ]}
            onPress={handleUpload}
            activeOpacity={0.85}
            disabled={uploading || !securityConfirmed}
          >
            {uploading ? (
              <>
                <ActivityIndicator color="#fff" size="small" />
                <Text style={s.uploadBtnText}>UPLOADING…</Text>
              </>
            ) : (
              <>
                <Ionicons name="cloud-upload-outline" size={20} color="#fff" />
                <Text style={s.uploadBtnText}>
                  UPLOAD {photos.length} PHOTO{photos.length !== 1 ? "S" : ""}
                </Text>
              </>
            )}
          </TouchableOpacity>
        </View>
      )}
    </SafeAreaView>
  );
}

const makeStyles = (c: ThemeColors) =>
  StyleSheet.create({
    safe: { flex: 1, backgroundColor: c.bg },

    header: {
      flexDirection: "row",
      alignItems: "flex-end",
      justifyContent: "space-between",
      paddingHorizontal: 24,
      paddingTop: 20,
      paddingBottom: 4,
    },
    eyebrow: {
      fontSize: 10,
      fontWeight: "700",
      color: c.accent,
      letterSpacing: 2.5,
      marginBottom: 4,
    },
    title: {
      fontSize: 32,
      fontWeight: "800",
      color: c.textBright,
      letterSpacing: -1,
      fontFamily: Platform.OS === "ios" ? "Georgia" : "serif",
    },
    trashBtn: {
      width: 40,
      height: 40,
      borderRadius: 12,
      backgroundColor: c.surface,
      borderWidth: 1,
      borderColor: c.border,
      alignItems: "center",
      justifyContent: "center",
      marginBottom: 4,
    },
    subtitle: {
      fontSize: 13,
      color: c.textFaint,
      paddingHorizontal: 24,
      marginBottom: 12,
    },

    eventBox: {
      marginHorizontal: 20,
      marginBottom: 12,
    },
    eventLabel: {
      fontSize: 10,
      fontWeight: "700",
      color: c.accent,
      letterSpacing: 2.5,
      marginBottom: 8,
    },
    eventSelect: {
      minHeight: 58,
      flexDirection: "row",
      alignItems: "center",
      gap: 12,
      borderRadius: 14,
      borderWidth: 1,
      borderColor: c.border,
      backgroundColor: c.surface,
      paddingHorizontal: 14,
      paddingVertical: 10,
    },
    eventSelectChosen: {
      borderColor: c.accent,
    },
    eventSelectDisabled: {
      opacity: 0.7,
    },
    eventSelectText: {
      flex: 1,
    },
    eventSelectTitle: {
      fontSize: 15,
      fontWeight: "700",
      color: c.textPrimary,
    },
    eventSelectHint: {
      marginTop: 2,
      fontSize: 11,
      color: c.textMuted,
    },
    eventErrorRow: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "space-between",
      gap: 12,
      marginTop: 7,
    },
    eventErrorText: {
      flex: 1,
      fontSize: 12,
      color: c.danger,
    },
    eventRetryText: {
      fontSize: 12,
      fontWeight: "700",
      color: c.accent,
    },
    eventMenuBackdrop: {
      flex: 1,
      justifyContent: "center",
      backgroundColor: "rgba(5,8,16,0.72)",
      paddingHorizontal: 20,
    },
    eventMenu: {
      width: "100%",
      maxWidth: 520,
      maxHeight: "72%",
      alignSelf: "center",
      backgroundColor: c.surface,
      borderWidth: 1,
      borderColor: c.border,
      borderRadius: 20,
      overflow: "hidden",
    },
    eventMenuHeader: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "space-between",
      padding: 18,
      borderBottomWidth: 1,
      borderBottomColor: c.border,
    },
    eventMenuEyebrow: {
      fontSize: 9,
      fontWeight: "700",
      color: c.accent,
      letterSpacing: 2,
      marginBottom: 3,
    },
    eventMenuTitle: {
      fontSize: 20,
      fontWeight: "800",
      color: c.textBright,
    },
    eventMenuClose: {
      width: 36,
      height: 36,
      borderRadius: 10,
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: c.bg,
    },
    eventMenuList: {
      flexGrow: 0,
    },
    eventMenuListContent: {
      padding: 12,
      gap: 8,
    },
    eventMenuEmpty: {
      minHeight: 160,
      alignItems: "center",
      justifyContent: "center",
      gap: 10,
      paddingHorizontal: 24,
    },
    eventMenuEmptyText: {
      color: c.textMuted,
      fontSize: 13,
      textAlign: "center",
    },
    eventOption: {
      minHeight: 64,
      flexDirection: "row",
      alignItems: "center",
      gap: 12,
      padding: 12,
      borderWidth: 1,
      borderColor: c.border,
      borderRadius: 14,
      backgroundColor: c.bg,
    },
    eventOptionSelected: {
      borderColor: c.accentStrong,
      backgroundColor: c.accentStrong,
    },
    eventOptionIcon: {
      width: 38,
      height: 38,
      borderRadius: 10,
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: "rgba(59,130,246,0.12)",
    },
    eventOptionText: {
      flex: 1,
    },
    eventOptionName: {
      color: c.textPrimary,
      fontSize: 14,
      fontWeight: "700",
    },
    eventOptionNameSelected: {
      color: "#fff",
    },
    eventOptionId: {
      color: c.textMuted,
      fontSize: 11,
      marginTop: 2,
    },
    eventOptionIdSelected: {
      color: "rgba(255,255,255,0.78)",
    },

    securityBox: {
      marginHorizontal: 20,
      marginBottom: 12,
      padding: 12,
      borderRadius: 14,
      backgroundColor: c.successBg,
      borderWidth: 1,
      borderColor: c.successBorder,
      flexDirection: "row",
      gap: 10,
      alignItems: "flex-start",
    },
    securityTitle: {
      color: c.successText,
      fontWeight: "800",
      fontSize: 13,
      marginBottom: 2,
    },
    securityText: {
      color: c.successTextSoft,
      fontSize: 12,
      lineHeight: 17,
    },

    empty: {
      flex: 1,
      paddingHorizontal: 20,
      justifyContent: "center",
      gap: 16,
    },
    dropZone: {
      backgroundColor: c.surface,
      borderRadius: 20,
      borderWidth: 1.5,
      borderColor: c.border,
      borderStyle: "dashed",
      alignItems: "center",
      paddingVertical: 52,
      paddingHorizontal: 24,
      gap: 12,
    },
    iconRing: {
      width: 80,
      height: 80,
      borderRadius: 40,
      backgroundColor: c.bg,
      borderWidth: 1.5,
      borderColor: c.border,
      alignItems: "center",
      justifyContent: "center",
      marginBottom: 4,
    },
    dropTitle: {
      fontSize: 20,
      fontWeight: "800",
      color: c.textBright,
      letterSpacing: -0.5,
      fontFamily: Platform.OS === "ios" ? "Georgia" : "serif",
    },
    dropSub: {
      fontSize: 13,
      color: c.textMuted,
      textAlign: "center",
      lineHeight: 20,
    },
    selectBadge: {
      flexDirection: "row",
      alignItems: "center",
      gap: 6,
      backgroundColor: c.accentStrong,
      paddingHorizontal: 18,
      paddingVertical: 9,
      borderRadius: 20,
      marginTop: 8,
      shadowColor: c.accentStrong,
      shadowOffset: { width: 0, height: 4 },
      shadowOpacity: 0.4,
      shadowRadius: 10,
      elevation: 6,
    },
    selectBadgeText: {
      fontSize: 12,
      fontWeight: "700",
      color: "#fff",
      letterSpacing: 1.8,
    },

    successBanner: {
      flexDirection: "row",
      alignItems: "center",
      gap: 8,
      backgroundColor: c.successBg,
      borderWidth: 1,
      borderColor: c.successBorder,
      borderRadius: 12,
      paddingHorizontal: 16,
      paddingVertical: 12,
    },
    successText: {
      fontSize: 14,
      color: c.successText,
      fontWeight: "600",
    },

    grid: {
      paddingHorizontal: 16,
      paddingBottom: 16,
      gap: 8,
    },
    gridRow: { gap: 8 },
    thumb: {
      borderRadius: 10,
      overflow: "hidden",
      backgroundColor: c.surface,
    },
    thumbImg: { width: "100%", height: "100%" },
    removeBtn: {
      position: "absolute",
      top: 4,
      right: 4,
      backgroundColor: "rgba(13,17,23,0.75)",
      borderRadius: 11,
    },
    addMore: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "center",
      gap: 8,
      backgroundColor: c.surface,
      borderRadius: 12,
      borderWidth: 1,
      borderColor: c.border,
      paddingVertical: 14,
      marginTop: 8,
    },
    addMoreText: {
      fontSize: 14,
      fontWeight: "600",
      color: c.accent,
    },

    footer: {
      paddingHorizontal: 20,
      paddingTop: 12,
      paddingBottom: Platform.OS === "ios" ? 8 : 16,
      borderTopWidth: 1,
      borderTopColor: c.border,
      backgroundColor: c.bg,
    },
    confirmRow: {
      flexDirection: "row",
      alignItems: "center",
      gap: 8,
      marginBottom: 12,
    },
    confirmText: {
      color: c.textPrimary,
      fontSize: 13,
      fontWeight: "600",
    },
    uploadBtn: {
      backgroundColor: c.accentStrong,
      borderRadius: 14,
      height: 54,
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "center",
      gap: 10,
      shadowColor: c.accentStrong,
      shadowOffset: { width: 0, height: 6 },
      shadowOpacity: 0.45,
      shadowRadius: 14,
      elevation: 8,
    },
    uploadBtnBusy: { opacity: 0.65 },
    uploadBtnDisabled: { opacity: 0.5 },
    uploadBtnText: {
      fontSize: 13,
      fontWeight: "800",
      color: "#fff",
      letterSpacing: 2,
    },
  });
