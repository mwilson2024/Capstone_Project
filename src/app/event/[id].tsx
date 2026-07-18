import { Ionicons } from "@expo/vector-icons";
import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Dimensions,
  FlatList,
  Image,
  Platform,
  SafeAreaView,
  StatusBar,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import Lightbox, { LightboxPhoto } from "@/components/Lightbox";
import { apiFetch } from "@/lib/api";
import { ThemeColors } from "@/theme/colors";
import { useTheme } from "@/theme/ThemeContext";

const { width: SCREEN_WIDTH } = Dimensions.get("window");
const NUM_COLS = 3;
const CELL = (SCREEN_WIDTH - 4) / NUM_COLS;

type EventInfo = {
  event_id: number;
  name: string;
  type: string;
  event_date: string;
  status: string;
};

type MediaItem = {
  id: number;
  display_url: string | null;
  original_file_name: string | null;
};

export default function EventDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { colors: c } = useTheme();
  const s = useMemo(() => makeStyles(c), [c]);
  const [event, setEvent] = useState<EventInfo | null>(null);
  const [photos, setPhotos] = useState<LightboxPhoto[]>([]);
  const [videoCount, setVideoCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!id) return;
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    (async () => {
      try {
        const [eventRes, mediaRes] = await Promise.all([
          apiFetch(`/events/${id}`, undefined, "GET", controller.signal),
          apiFetch(`/events/${id}/media?dataType=both`, undefined, "GET", controller.signal),
        ]);
        setEvent(eventRes.event);
        setVideoCount(mediaRes.video_count ?? 0);
        setPhotos(
          (mediaRes.photos ?? [])
            .filter((p: MediaItem) => p.display_url)
            .map((p: MediaItem) => ({ id: String(p.id), uri: p.display_url as string }))
        );
        setLoading(false);
      } catch (err: any) {
        if (err.name === "AbortError") return;
        setError(err.message ?? "Could not load event.");
        setLoading(false);
      }
    })();

    return () => controller.abort();
  }, [id, attempt]);

  const dateLabel = useMemo(() => {
    if (!event?.event_date) return "";
    const [y, m, d] = event.event_date.slice(0, 10).split("-").map(Number);
    return new Date(y, m - 1, d).toLocaleDateString();
  }, [event?.event_date]);

  return (
    <SafeAreaView style={s.safe}>
      <StatusBar barStyle={c.statusBar} />

      <View style={s.header}>
        <TouchableOpacity
          style={s.backBtn}
          onPress={() => router.back()}
          accessibilityLabel="Back"
        >
          <Ionicons name="chevron-back" size={24} color={c.textBright} />
        </TouchableOpacity>
        <View style={s.headerText}>
          <Text style={s.title} numberOfLines={1}>
            {event?.name ?? "Event"}
          </Text>
          {event && (
            <Text style={s.meta}>
              {event.type} · {dateLabel} · {event.status}
            </Text>
          )}
        </View>
      </View>

      {loading ? (
        <ActivityIndicator color={c.accent} style={{ marginTop: 48 }} />
      ) : error ? (
        <View style={s.errorBox}>
          <Text style={s.errorText}>{error}</Text>
          <TouchableOpacity
            style={s.retryBtn}
            onPress={() => setAttempt((n) => n + 1)}
            activeOpacity={0.8}
          >
            <Ionicons name="refresh" size={16} color="#fff" />
            <Text style={s.retryText}>Try Again</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <>
          <Text style={s.counts}>
            {photos.length} photo{photos.length !== 1 ? "s" : ""}
            {videoCount > 0 ? ` · ${videoCount} video${videoCount !== 1 ? "s" : ""}` : ""}
          </Text>

          {photos.length === 0 ? (
            <View style={s.empty}>
              <Ionicons name="images-outline" size={40} color={c.textFaint} />
              <Text style={s.emptyText}>No photos in this event yet.</Text>
            </View>
          ) : (
            <FlatList
              data={photos}
              numColumns={NUM_COLS}
              keyExtractor={(item) => item.id}
              contentContainerStyle={s.grid}
              renderItem={({ item, index }) => (
                <TouchableOpacity
                  activeOpacity={0.85}
                  onPress={() => setLightboxIndex(index)}
                  style={{ width: CELL, height: CELL, padding: 1 }}
                >
                  <Image
                    source={{ uri: item.uri }}
                    style={s.cellImage}
                    resizeMode="cover"
                  />
                </TouchableOpacity>
              )}
            />
          )}
        </>
      )}

      {lightboxIndex !== null && (
        <Lightbox
          photos={photos}
          startIndex={lightboxIndex}
          onClose={() => setLightboxIndex(null)}
        />
      )}
    </SafeAreaView>
  );
}

const makeStyles = (c: ThemeColors) =>
  StyleSheet.create({
    safe: { flex: 1, backgroundColor: c.bg },
    header: {
      flexDirection: "row",
      alignItems: "center",
      paddingHorizontal: 16,
      paddingVertical: 14,
      gap: 12,
    },
    backBtn: {
      width: 36,
      height: 36,
      borderRadius: 10,
      backgroundColor: c.surface,
      borderWidth: 1,
      borderColor: c.border,
      alignItems: "center",
      justifyContent: "center",
    },
    headerText: { flex: 1, marginRight: 48 },
    title: {
      fontSize: 20,
      fontWeight: "800",
      color: c.textBright,
      letterSpacing: -0.4,
      fontFamily: Platform.OS === "ios" ? "Georgia" : "serif",
    },
    meta: { fontSize: 12, color: c.textMuted, marginTop: 2 },
    counts: {
      fontSize: 13,
      color: c.textFaint,
      paddingHorizontal: 16,
      marginBottom: 8,
    },
    grid: { paddingBottom: 24 },
    cellImage: {
      width: "100%",
      height: "100%",
      borderRadius: 4,
      backgroundColor: c.surface,
    },
    empty: {
      flex: 1,
      alignItems: "center",
      justifyContent: "center",
      gap: 12,
      paddingBottom: 80,
    },
    emptyText: { fontSize: 14, color: c.textMuted },
    errorBox: {
      alignItems: "center",
      marginTop: 48,
      paddingHorizontal: 24,
      gap: 16,
    },
    errorText: { color: c.danger, textAlign: "center", fontSize: 14 },
    retryBtn: {
      flexDirection: "row",
      alignItems: "center",
      gap: 8,
      backgroundColor: c.accentStrong,
      borderRadius: 12,
      paddingHorizontal: 20,
      paddingVertical: 11,
    },
    retryText: { color: "#fff", fontSize: 14, fontWeight: "700" },
  });
