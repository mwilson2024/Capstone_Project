import { Ionicons } from "@expo/vector-icons";
import * as ImagePicker from "expo-image-picker";
import { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Dimensions,
  FlatList,
  Image,
  Platform,
  SafeAreaView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { API_URL, apiFetch, hasToken } from "@/lib/api";
import { ThemeColors } from "@/theme/colors";
import { useTheme } from "@/theme/ThemeContext";

const { width: SCREEN_WIDTH } = Dimensions.get("window");
const THUMB = (SCREEN_WIDTH - 56) / 3;

const MAX_PHOTOS = 20;
const QR_TOKEN = "QR_TOKEN_HERE";
const GUEST_ID = 0;

type PickedPhoto = { id: string; uri: string };
type EventOption = { event_id: number; name: string };

export default function UploadScreen() {
  const { colors: c } = useTheme();
  const s = useMemo(() => makeStyles(c), [c]);
  const [photos, setPhotos] = useState<PickedPhoto[]>([]);
  const [uploading, setUploading] = useState(false);
  const [done, setDone] = useState(false);
  const [securityConfirmed, setSecurityConfirmed] = useState(false);
  const [eventId, setEventId] = useState("");
  const [events, setEvents] = useState<EventOption[]>([]);

  useEffect(() => {
    if (!hasToken()) return;
    apiFetch("/events/mine")
      .then((res) => setEvents(Array.isArray(res) ? res : res.events ?? []))
      .catch(() => {});
  }, []);

  const isValidImage = (uri: string) => {
    const lower = uri.toLowerCase();
    return (
      lower.endsWith(".jpg") ||
      lower.endsWith(".jpeg") ||
      lower.endsWith(".png") ||
      lower.includes("image")
    );
  };

  const validateUpload = () => {
    const id = Number(eventId);
    if (!Number.isInteger(id) || id <= 0) {
      Alert.alert("No Event Selected", "Choose which event these photos belong to.");
      return false;
    }

    if (!QR_TOKEN || QR_TOKEN === "QR_TOKEN_HERE" || !GUEST_ID) {
      Alert.alert("Security Error", "Missing valid QR event token or guest ID.");
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

    const invalidPhoto = photos.find((photo) => !isValidImage(photo.uri));
    if (invalidPhoto) {
      Alert.alert("Invalid File", "Only JPG, JPEG, and PNG image files are allowed.");
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
      const picked: PickedPhoto[] = result.assets.map((a, i) => ({
        id: `${Date.now()}-${i}`,
        uri: a.uri,
      }));

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

      formData.append("eventID", String(Number(eventId)));
      formData.append("qrToken", QR_TOKEN);
      formData.append("guestID", String(GUEST_ID));

      photos.forEach((photo, index) => {
        formData.append("files", {
          uri: photo.uri,
          name: `photo_${index}.jpg`,
          type: "image/jpeg",
        } as any);
      });

      const response = await fetch(`${API_URL}/upload/guest`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(typeof err.detail === "string" ? err.detail : "Upload failed");
      }

      const result = await response.json();
      console.log(`Uploaded ${result.uploaded} photos`);

      setDone(true);
      setPhotos([]);
      setSecurityConfirmed(false);

      Alert.alert(
        "Upload Submitted",
        "Photos were uploaded and marked for admin review."
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
        {events.length > 0 ? (
          <View style={s.chipRow}>
            {events.map((ev) => (
              <TouchableOpacity
                key={ev.event_id}
                style={[s.chip, Number(eventId) === ev.event_id && s.chipSelected]}
                onPress={() => setEventId(String(ev.event_id))}
                activeOpacity={0.8}
              >
                <Text
                  style={[
                    s.chipText,
                    Number(eventId) === ev.event_id && s.chipTextSelected,
                  ]}
                >
                  {ev.name}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        ) : (
          <TextInput
            style={s.eventInput}
            placeholder="Event ID"
            placeholderTextColor={c.textMuted}
            keyboardType="number-pad"
            value={eventId}
            onChangeText={setEventId}
          />
        )}
      </View>

      <View style={s.securityBox}>
        <Ionicons name="shield-checkmark-outline" size={20} color={c.successText} />
        <View style={{ flex: 1 }}>
          <Text style={s.securityTitle}>Security Check</Text>
          <Text style={s.securityText}>
            Only image files are allowed. Uploads use the event QR token and are submitted for admin review.
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
    chipRow: {
      flexDirection: "row",
      flexWrap: "wrap",
      gap: 8,
    },
    chip: {
      paddingHorizontal: 14,
      paddingVertical: 8,
      borderRadius: 20,
      backgroundColor: c.surface,
      borderWidth: 1,
      borderColor: c.border,
    },
    chipSelected: {
      backgroundColor: c.accentStrong,
      borderColor: c.accentStrong,
    },
    chipText: {
      fontSize: 13,
      fontWeight: "600",
      color: c.textPrimary,
    },
    chipTextSelected: {
      color: "#fff",
    },
    eventInput: {
      height: 46,
      borderRadius: 12,
      borderWidth: 1.5,
      borderColor: c.border,
      backgroundColor: c.surface,
      paddingHorizontal: 14,
      fontSize: 15,
      color: c.textPrimary,
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
