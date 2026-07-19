import { Ionicons } from "@expo/vector-icons";
import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Dimensions,
  FlatList,
  Image,
  Modal,
  Platform,
  SafeAreaView,
  StatusBar,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import GeneratedVideoPlayer from "@/components/GeneratedVideoPlayer";
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
  title?: string | null;
  duration_seconds?: number | null;
};

type UploadedVideo = {
  id: string;
  uri: string;
  title: string;
  durationSeconds: number | null;
};

type EventMediaResponse = {
  photos: MediaItem[];
  videos: MediaItem[];
};

function formatDuration(seconds: number | null) {
  if (seconds === null || !Number.isFinite(seconds) || seconds < 0) {
    return "Video";
  }

  const rounded = Math.round(seconds);
  const minutes = Math.floor(rounded / 60);
  const remainingSeconds = rounded % 60;
  return `${minutes}:${String(remainingSeconds).padStart(2, "0")}`;
}

function UploadedVideoModal({
  eventId,
  video,
  onClose,
}: {
  eventId: string;
  video: UploadedVideo;
  onClose: () => void;
}) {
  const { colors: c } = useTheme();
  const [freshVideo, setFreshVideo] = useState<UploadedVideo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const media = await apiFetch<EventMediaResponse>(
          `/events/${eventId}/media?dataType=videos`
        );
        const current = (media.videos ?? []).find(
          (item) => String(item.id) === video.id
        );

        if (!current?.display_url) {
          throw new Error("This uploaded video is no longer available.");
        }

        if (!cancelled) {
          setFreshVideo({
            ...video,
            uri: current.display_url,
            title:
              current.title ||
              current.original_file_name ||
              video.title,
            durationSeconds:
              current.duration_seconds ?? video.durationSeconds,
          });
        }
      } catch (caught) {
        if (!cancelled) {
          setError(
            caught instanceof Error
              ? caught.message
              : "The uploaded video could not be loaded."
          );
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [eventId, video]);

  return (
    <Modal visible animationType="fade" statusBarTranslucent>
      <SafeAreaView style={[videoModal.container, { backgroundColor: c.bg }]}>
        <StatusBar barStyle={c.statusBar} />
        <View style={videoModal.header}>
          <View style={videoModal.headerText}>
            <Text
              numberOfLines={1}
              style={[videoModal.title, { color: c.textBright }]}
            >
              {video.title}
            </Text>
            <Text style={[videoModal.meta, { color: c.textMuted }]}>
              Uploaded video
            </Text>
          </View>
          <TouchableOpacity
            accessibilityLabel="Close video"
            onPress={onClose}
            style={[
              videoModal.closeButton,
              { backgroundColor: c.surface, borderColor: c.border },
            ]}
          >
            <Ionicons name="close" size={24} color={c.textBright} />
          </TouchableOpacity>
        </View>
        <View style={videoModal.playerArea}>
          {error ? (
            <View style={videoModal.center}>
              <Ionicons
                name="alert-circle-outline"
                size={42}
                color={c.danger}
              />
              <Text style={[videoModal.error, { color: c.danger }]}>
                {error}
              </Text>
            </View>
          ) : freshVideo ? (
            <GeneratedVideoPlayer
              key={freshVideo.uri}
              streamUrl={freshVideo.uri}
            />
          ) : (
            <View style={videoModal.center}>
              <ActivityIndicator size="large" color={c.accent} />
              <Text style={{ color: c.textMuted }}>Loading video...</Text>
            </View>
          )}
        </View>
      </SafeAreaView>
    </Modal>
  );
}

export default function EventDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { colors: c } = useTheme();
  const s = useMemo(() => makeStyles(c), [c]);
  const [event, setEvent] = useState<EventInfo | null>(null);
  const [photos, setPhotos] = useState<LightboxPhoto[]>([]);
  const [videos, setVideos] = useState<UploadedVideo[]>([]);
  const [mediaTab, setMediaTab] = useState<"photos" | "videos">("photos");
  const [selectedVideo, setSelectedVideo] = useState<UploadedVideo | null>(null);
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
        setPhotos(
          (mediaRes.photos ?? [])
            .filter((p: MediaItem) => p.display_url)
            .map((p: MediaItem) => ({ id: String(p.id), uri: p.display_url as string }))
        );
        const loadedVideos = (mediaRes.videos ?? [])
          .filter((video: MediaItem) => video.display_url)
          .map((video: MediaItem) => ({
            id: String(video.id),
            uri: video.display_url as string,
            title:
              video.title ||
              video.original_file_name ||
              `Uploaded video ${video.id}`,
            durationSeconds: video.duration_seconds ?? null,
          }));
        setVideos(loadedVideos);
        if ((mediaRes.photos ?? []).length === 0 && loadedVideos.length > 0) {
          setMediaTab("videos");
        }
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
            {videos.length > 0 ? ` · ${videos.length} video${videos.length !== 1 ? "s" : ""}` : ""}
          </Text>

          <View style={s.tabs}>
            <TouchableOpacity
              onPress={() => setMediaTab("photos")}
              style={[
                s.tab,
                mediaTab === "photos" && { backgroundColor: c.accentStrong },
              ]}
            >
              <Ionicons
                name="images-outline"
                size={17}
                color={mediaTab === "photos" ? "#fff" : c.textMuted}
              />
              <Text
                style={[
                  s.tabText,
                  { color: mediaTab === "photos" ? "#fff" : c.textMuted },
                ]}
              >
                Photos ({photos.length})
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              onPress={() => setMediaTab("videos")}
              style={[
                s.tab,
                mediaTab === "videos" && { backgroundColor: c.accentStrong },
              ]}
            >
              <Ionicons
                name="videocam-outline"
                size={18}
                color={mediaTab === "videos" ? "#fff" : c.textMuted}
              />
              <Text
                style={[
                  s.tabText,
                  { color: mediaTab === "videos" ? "#fff" : c.textMuted },
                ]}
              >
                Videos ({videos.length})
              </Text>
            </TouchableOpacity>
          </View>

          {mediaTab === "photos" ? (
            photos.length === 0 ? (
              <View style={s.empty}>
                <Ionicons name="images-outline" size={40} color={c.textFaint} />
                <Text style={s.emptyText}>No photos in this event yet.</Text>
              </View>
            ) : (
              <FlatList
                key="photos"
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
            )
          ) : (
            <FlatList
              key="videos"
              data={videos}
              keyExtractor={(item) => item.id}
              contentContainerStyle={[
                s.videoList,
                videos.length === 0 && s.emptyList,
              ]}
              ListEmptyComponent={
                <View style={s.empty}>
                  <Ionicons
                    name="videocam-outline"
                    size={42}
                    color={c.textFaint}
                  />
                  <Text style={s.emptyText}>No uploaded videos yet.</Text>
                </View>
              }
              renderItem={({ item }) => (
                <TouchableOpacity
                  activeOpacity={0.85}
                  onPress={() => setSelectedVideo(item)}
                  style={[
                    s.videoRow,
                    { backgroundColor: c.surface, borderColor: c.border },
                  ]}
                >
                  <View
                    style={[
                      s.videoIcon,
                      { backgroundColor: c.accentStrong },
                    ]}
                  >
                    <Ionicons name="play" size={24} color="#fff" />
                  </View>
                  <View style={s.videoInfo}>
                    <Text numberOfLines={1} style={s.videoTitle}>
                      {item.title}
                    </Text>
                    <Text style={s.videoMeta}>
                      {formatDuration(item.durationSeconds)}
                    </Text>
                  </View>
                  <Ionicons
                    name="chevron-forward"
                    size={20}
                    color={c.textFaint}
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
      {selectedVideo && id && (
        <UploadedVideoModal
          eventId={id}
          video={selectedVideo}
          onClose={() => setSelectedVideo(null)}
        />
      )}
    </SafeAreaView>
  );
}

const videoModal = StyleSheet.create({
  container: { flex: 1 },
  header: {
    width: "100%",
    maxWidth: 1100,
    alignSelf: "center",
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingVertical: 16,
    gap: 16,
  },
  headerText: { flex: 1 },
  title: { fontSize: 20, fontWeight: "800" },
  meta: { fontSize: 12, marginTop: 2 },
  closeButton: {
    width: 42,
    height: 42,
    borderRadius: 12,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  playerArea: {
    flex: 1,
    justifyContent: "center",
    paddingHorizontal: 20,
    paddingBottom: 24,
  },
  center: {
    minHeight: 280,
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
  },
  error: { textAlign: "center", paddingHorizontal: 24 },
});

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
    tabs: {
      flexDirection: "row",
      alignSelf: "center",
      gap: 8,
      paddingHorizontal: 16,
      paddingBottom: 14,
    },
    tab: {
      minHeight: 38,
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "center",
      gap: 7,
      borderRadius: 20,
      paddingHorizontal: 16,
      paddingVertical: 8,
    },
    tabText: { fontSize: 13, fontWeight: "700" },
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
    emptyList: { flexGrow: 1, justifyContent: "center" },
    videoList: {
      width: "100%",
      maxWidth: 900,
      alignSelf: "center",
      paddingHorizontal: 16,
      paddingBottom: 24,
      gap: 10,
    },
    videoRow: {
      minHeight: 84,
      flexDirection: "row",
      alignItems: "center",
      gap: 14,
      borderWidth: 1,
      borderRadius: 14,
      padding: 12,
    },
    videoIcon: {
      width: 58,
      height: 58,
      borderRadius: 12,
      alignItems: "center",
      justifyContent: "center",
    },
    videoInfo: { flex: 1 },
    videoTitle: {
      color: c.textPrimary,
      fontSize: 15,
      fontWeight: "700",
    },
    videoMeta: { color: c.textMuted, fontSize: 12, marginTop: 4 },
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
