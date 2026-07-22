import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Dimensions,
  Image,
  Platform,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { apiFetch } from "@/lib/api";
import { ThemeColors } from "@/theme/colors";
import { useTheme } from "@/theme/ThemeContext";

const { width: SCREEN_WIDTH } = Dimensions.get("window");
const CARD_WIDTH = (SCREEN_WIDTH - 48) / 2;

type Photo = { id: string; uri: string; isSensitive: boolean };
type Gallery = {
  id: string;
  title: string;
  date: string;
  photoCount: number;
  videoCount: number;
  coverColor: string;
  accentColor: string;
  photos: Photo[];
};

type EventRecord = {
  event_id: number;
  name: string;
  event_date: string;
};

type EventsResponse = {
  events: EventRecord[];
};

type MediaRecord = {
  id: number;
  display_url: string | null;
  nudity_check?: boolean | string | null;
};

type EventMediaResponse = {
  photos: MediaRecord[];
  video_count: number;
  photo_total?: number;
  video_total?: number;
};

const GALLERY_COLORS = [
  { cover: "#1A2F5A", accent: "#3B82F6" },
  { cover: "#312E81", accent: "#8B5CF6" },
  { cover: "#164E63", accent: "#06B6D4" },
  { cover: "#78350F", accent: "#F59E0B" },
];

function isSensitivePhoto(photo: MediaRecord) {
  return (
    photo.nudity_check === true ||
    (typeof photo.nudity_check === "string" &&
      ["1", "true", "yes"].includes(photo.nudity_check.toLowerCase()))
  );
}

function formatEventDate(value: string) {
  const [year, month, day] = value.slice(0, 10).split("-").map(Number);
  const date = new Date(year, month - 1, day);

  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

async function loadGallery(
  event: EventRecord,
  index: number,
  signal?: AbortSignal
): Promise<Gallery> {
  const media = await apiFetch<EventMediaResponse>(
    `/events/${event.event_id}/media?dataType=both&limit=1&offset=0`,
    undefined,
    "GET",
    signal
  );
  const palette = GALLERY_COLORS[index % GALLERY_COLORS.length];
  const photos = (media.photos ?? [])
    .filter(
      (photo): photo is MediaRecord & { display_url: string } =>
        typeof photo.display_url === "string" && photo.display_url.length > 0
    )
    .map((photo) => ({
      id: String(photo.id),
      uri: photo.display_url,
      isSensitive: isSensitivePhoto(photo),
    }));

  return {
    id: String(event.event_id),
    title: event.name,
    date: formatEventDate(event.event_date),
    photoCount: media.photo_total ?? photos.length,
    videoCount: media.video_total ?? media.video_count ?? 0,
    coverColor: palette.cover,
    accentColor: palette.accent,
    photos,
  };
}

// Gallery Card
function GalleryCard({
  gallery,
  onPress,
}: {
  gallery: Gallery;
  onPress: () => void;
}) {
  const { colors: c } = useTheme();
  const gc = useMemo(() => makeCardStyles(c), [c]);
  return (
    <TouchableOpacity
      style={[gc.card, { width: CARD_WIDTH }]}
      activeOpacity={0.88}
      onPress={onPress}
    >
      <View style={[gc.cover, { backgroundColor: gallery.coverColor }]}>
        {gallery.photos[0] ? (
          <Image
            source={{ uri: gallery.photos[0].uri }}
            style={gc.coverImage}
            resizeMode="cover"
            blurRadius={gallery.photos[0].isSensitive ? 32 : 0}
          />
        ) : (
          <View style={gc.emptyCover}>
            <Ionicons name="videocam" size={34} color="#fff" />
          </View>
        )}
        {gallery.photos[0]?.isSensitive ? (
          <View style={gc.sensitiveBadge} pointerEvents="none">
            <Ionicons name="eye-off" size={13} color="#fff" />
            <Text style={gc.sensitiveText}>Blurred</Text>
          </View>
        ) : null}
        <View style={gc.badges}>
          <View style={[gc.badge, { backgroundColor: gallery.accentColor }]}>
            <Ionicons name="images" size={10} color="#fff" />
            <Text style={gc.badgeText}>{gallery.photoCount}</Text>
          </View>
          {gallery.videoCount > 0 ? (
            <View style={[gc.badge, { backgroundColor: "#111827" }]}>
              <Ionicons name="videocam" size={11} color="#fff" />
              <Text style={gc.badgeText}>{gallery.videoCount}</Text>
            </View>
          ) : null}
        </View>
        <View style={[gc.accentBar, { backgroundColor: gallery.accentColor }]} />
      </View>
      <View style={gc.info}>
        <Text style={gc.cardTitle} numberOfLines={1}>
          {gallery.title}
        </Text>
        <Text style={gc.cardDate}>{gallery.date}</Text>
      </View>
    </TouchableOpacity>
  );
}

const makeCardStyles = (c: ThemeColors) =>
  StyleSheet.create({
    card: {
      backgroundColor: c.surface,
      borderRadius: 14,
      overflow: "hidden",
      borderWidth: 1,
      borderColor: c.border,
    },
    cover: { height: CARD_WIDTH * 0.75, width: "100%", overflow: "hidden" },
    coverImage: { width: "100%", height: "100%", opacity: 0.85 },
    sensitiveBadge: {
      position: "absolute",
      left: 8,
      bottom: 10,
      flexDirection: "row",
      alignItems: "center",
      gap: 5,
      backgroundColor: "rgba(5,8,16,0.78)",
      paddingHorizontal: 8,
      paddingVertical: 5,
      borderRadius: 14,
    },
    sensitiveText: { color: "#fff", fontSize: 10, fontWeight: "700" },
    emptyCover: {
      width: "100%",
      height: "100%",
      alignItems: "center",
      justifyContent: "center",
      opacity: 0.8,
    },
    badges: {
      position: "absolute",
      top: 8,
      right: 8,
      flexDirection: "row",
      gap: 6,
    },
    badge: {
      flexDirection: "row",
      alignItems: "center",
      gap: 4,
      paddingHorizontal: 8,
      paddingVertical: 4,
      borderRadius: 20,
    },
    badgeText: { color: "#fff", fontSize: 10, fontWeight: "700" },
    accentBar: {
      position: "absolute",
      bottom: 0,
      left: 0,
      right: 0,
      height: 2,
      opacity: 0.7,
    },
    info: { padding: 10 },
    cardTitle: {
      fontSize: 13,
      fontWeight: "700",
      color: c.textPrimary,
      letterSpacing: -0.2,
      fontFamily: Platform.OS === "ios" ? "Georgia" : "serif",
    },
    cardDate: { fontSize: 11, color: c.textMuted, marginTop: 2 },
  });

// Gallery Screen
export default function GalleryScreen() {
  const { colors: c } = useTheme();
  const styles = useMemo(() => makeStyles(c), [c]);
  const [galleries, setGalleries] = useState<Gallery[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    (async () => {
      try {
        const response = await apiFetch<EventsResponse>(
          "/users/me/events",
          undefined,
          "GET",
          controller.signal
        );
        const loaded: Gallery[] = [];
        for (const [index, event] of response.events.entries()) {
          if (controller.signal.aborted) return;
          loaded.push(await loadGallery(event, index, controller.signal));
        }
        setGalleries(loaded);
        setLoading(false);
      } catch (err: any) {
        if (err.name === "AbortError") return;
        setError(err.message);
        setLoading(false);
      }
    })();

    return () => controller.abort();
  }, []);

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle={c.statusBar} />
      <View style={styles.container}>

        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.eyebrow}>YOUR EVENTS</Text>
            <Text style={styles.title}>Galleries</Text>
          </View>
          <TouchableOpacity style={styles.searchBtn}>
            <Ionicons name="search" size={20} color={c.textMuted} />
          </TouchableOpacity>
        </View>

        <Text style={styles.subtitle}>{galleries.length} saved events</Text>

        {loading ? (
          <ActivityIndicator color={c.accent} style={{ marginTop: 40 }} />
        ) : error ? (
          <Text style={styles.errorText}>{error}</Text>
        ) : (
          <ScrollView
            showsVerticalScrollIndicator={false}
            contentContainerStyle={styles.grid}
          >
            <View style={styles.row}>
              {galleries.map((gallery) => (
                <GalleryCard
                  key={gallery.id}
                  gallery={gallery}
                  onPress={() =>
                    router.push({
                      pathname: "/event/[id]",
                      params: { id: gallery.id },
                    })
                  }
                />
              ))}
            </View>
          </ScrollView>
        )}
        <View style={styles.floatingActions}>
          <TouchableOpacity
            style={[styles.floatingButton, styles.chatButton]}
            activeOpacity={0.86}
            onPress={() => router.push("/chatbot")}
            accessibilityLabel="Open video assistant"
          >
            <Ionicons name="chatbubble-ellipses" size={22} color="#fff" />
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.floatingButton}
            activeOpacity={0.86}
            onPress={() => router.push("/upload")}
            accessibilityLabel="Upload photos"
          >
            <Ionicons name="add" size={29} color="#fff" />
          </TouchableOpacity>
        </View>
      </View>
    </SafeAreaView>
  );
}

const makeStyles = (c: ThemeColors) =>
  StyleSheet.create({
    safe: { flex: 1, backgroundColor: c.bg },
    container: { flex: 1, backgroundColor: c.bg },
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
    searchBtn: {
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
      marginBottom: 20,
    },
    errorText: {
      color: c.danger,
      textAlign: "center",
      marginTop: 40,
      paddingHorizontal: 24,
    },
    grid: { paddingHorizontal: 20, paddingBottom: 24 },
    row: { flexDirection: "row", flexWrap: "wrap", gap: 12 },
    floatingActions: {
      position: "absolute",
      right: 22,
      bottom: 22,
      alignItems: "center",
      gap: 11,
    },
    floatingButton: {
      width: 58,
      height: 58,
      borderRadius: 19,
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: c.accentStrong,
      borderWidth: 1,
      borderColor: c.accent,
      shadowColor: "#000",
      shadowOffset: { width: 0, height: 7 },
      shadowOpacity: 0.35,
      shadowRadius: 10,
      elevation: 9,
    },
    chatButton: {
      width: 48,
      height: 48,
      borderRadius: 16,
      backgroundColor: "#7C3AED",
      borderColor: "#8B5CF6",
    },
  });
