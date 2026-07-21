import { Ionicons } from "@expo/vector-icons";
import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
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
  useWindowDimensions,
  View,
} from "react-native";
import GeneratedVideoPlayer from "@/components/GeneratedVideoPlayer";
import Lightbox, { LightboxPhoto } from "@/components/Lightbox";
import { apiFetch } from "@/lib/api";
import { useCurrentEvent } from "@/lib/CurrentEventContext";
import { downloadPhoto } from "@/lib/downloadPhoto";
import { ThemeColors } from "@/theme/colors";
import { useTheme } from "@/theme/ThemeContext";

const NUM_COLS = 3;
const MEDIA_PAGE_SIZE = 30;

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
  nudity_check?: boolean | string | null;
  filter_status?: string | null;
  filter_reason?: string | null;
  user_approved?: boolean | number | string | null;
  image_hash?: string | null;
};

type EventPhoto = LightboxPhoto & {
  filterStatus: string | null;
  filterReason: string | null;
  userApproved: boolean;
  imageHash: string | null;
};

type UploadedVideo = {
  id: string;
  uri: string;
  title: string;
  durationSeconds: number | null;
};

type GeneratedVideo = {
  id: string;
  title: string;
  durationSeconds: number | null;
};

type EventMediaResponse = {
  photos: MediaItem[];
  videos: MediaItem[];
  photo_count?: number;
  video_count?: number;
  photo_total?: number;
  video_total?: number;
  has_more_photos?: boolean;
  has_more_videos?: boolean;
  offset?: number;
  limit?: number;
};

type GeneratedVideoRecord = {
  gen_vid_id: number;
  title: string | null;
  file_name: string | null;
  status: string;
  duration_seconds: number | null;
};

type GeneratedVideosResponse = {
  videos: GeneratedVideoRecord[];
};

type SlideshowPreferenceResponse = {
  message: string;
  photo: {
    photo_id: number;
    filter_status: string | null;
    filter_reason: string | null;
    user_approved: boolean | number | string | null;
  };
};

const QUALITY_FILTER_REASONS = new Set([
  "low_resolution",
  "blurry",
  "single_color",
  "dark",
  "bright",
  "low_contrast",
]);

function isSensitivePhoto(photo: MediaItem) {
  return (
    photo.nudity_check === true ||
    (typeof photo.nudity_check === "string" &&
      ["1", "true", "yes"].includes(photo.nudity_check.toLowerCase()))
  );
}

function isUserApproved(value: boolean | number | string | null | undefined) {
  return (
    value === true ||
    value === 1 ||
    (typeof value === "string" &&
      ["1", "true", "yes"].includes(value.toLowerCase()))
  );
}

function hasQualityFilterRejection(reason: string | null | undefined) {
  return Boolean(
    reason
      ?.split(",")
      .some((value) => QUALITY_FILTER_REASONS.has(value.trim().toLowerCase()))
  );
}

function getPhotoFileName(photo: EventPhoto) {
  try {
    const pathName = new URL(photo.uri).pathname;
    const urlName = decodeURIComponent(pathName.split("/").pop() ?? "");
    if (/\.[a-zA-Z0-9]{2,5}$/.test(urlName)) return urlName;
  } catch {
    // Use the safe fallback below for relative or malformed URLs.
  }

  return `photo-${photo.id}.jpg`;
}

function mapPhotos(items: MediaItem[]): EventPhoto[] {
  return dedupePhotos(
    items
    .filter((photo) => photo.display_url)
    .map((photo) => ({
      id: String(photo.id),
      uri: photo.display_url as string,
      isSensitive: isSensitivePhoto(photo),
      filterStatus: photo.filter_status ?? null,
      filterReason: photo.filter_reason ?? null,
      userApproved: isUserApproved(photo.user_approved),
      imageHash: photo.image_hash ?? null,
    }))
  );
}

function getPhotoUriKey(uri: string) {
  try {
    const parsed = new URL(uri);
    return `${parsed.origin}${parsed.pathname}`.toLowerCase();
  } catch {
    return uri.split(/[?#]/, 1)[0].toLowerCase();
  }
}

function dedupePhotos(items: EventPhoto[]) {
  const ids = new Set<string>();
  const uris = new Set<string>();
  const hashes: string[] = [];

  return items.filter((photo) => {
    const uriKey = getPhotoUriKey(photo.uri);
    const imageHash = photo.imageHash?.trim().toLowerCase() || null;
    const matchesHash = Boolean(
      imageHash &&
        hashes.some(
          (existingHash) => perceptualHashDistance(existingHash, imageHash) <= 6
        )
    );

    if (ids.has(photo.id) || uris.has(uriKey) || matchesHash) return false;
    ids.add(photo.id);
    uris.add(uriKey);
    if (imageHash) hashes.push(imageHash);
    return true;
  });
}

function perceptualHashDistance(left: string, right: string) {
  if (left.length !== right.length || !/^[0-9a-f]+$/i.test(left + right)) {
    return Number.POSITIVE_INFINITY;
  }

  let distance = 0;
  for (let index = 0; index < left.length; index += 1) {
    let differentBits =
      Number.parseInt(left[index], 16) ^ Number.parseInt(right[index], 16);
    while (differentBits > 0) {
      distance += differentBits & 1;
      differentBits >>= 1;
    }
  }
  return distance;
}

function mapUploadedVideos(items: MediaItem[]): UploadedVideo[] {
  return items
    .filter((video) => video.display_url)
    .map((video) => ({
      id: String(video.id),
      uri: video.display_url as string,
      title:
        video.title ||
        video.original_file_name ||
        `Uploaded video ${video.id}`,
      durationSeconds: video.duration_seconds ?? null,
    }));
}

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
        let offset = 0;
        let current: MediaItem | undefined;

        do {
          const media = await apiFetch<EventMediaResponse>(
            `/events/${eventId}/media?dataType=videos&limit=100&offset=${offset}`
          );
          current = (media.videos ?? []).find(
            (item) => String(item.id) === video.id
          );
          offset += media.video_count ?? media.videos?.length ?? 0;

          if (current || !media.has_more_videos || cancelled) break;
        } while (true);

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
  const { width: viewportWidth } = useWindowDimensions();
  const photoCellSize = viewportWidth / NUM_COLS;
  const { colors: c } = useTheme();
  const { setCurrentEvent } = useCurrentEvent();
  const s = useMemo(() => makeStyles(c), [c]);
  const [event, setEvent] = useState<EventInfo | null>(null);
  const [photos, setPhotos] = useState<EventPhoto[]>([]);
  const [videos, setVideos] = useState<UploadedVideo[]>([]);
  const [photoTotal, setPhotoTotal] = useState(0);
  const [videoTotal, setVideoTotal] = useState(0);
  const [photoOffset, setPhotoOffset] = useState(0);
  const [videoOffset, setVideoOffset] = useState(0);
  const [hasMorePhotos, setHasMorePhotos] = useState(false);
  const [hasMoreVideos, setHasMoreVideos] = useState(false);
  const [loadingMorePhotos, setLoadingMorePhotos] = useState(false);
  const [loadingMoreVideos, setLoadingMoreVideos] = useState(false);
  const loadingMorePhotosRef = useRef(false);
  const loadingMoreVideosRef = useRef(false);
  const [generatedVideos, setGeneratedVideos] = useState<GeneratedVideo[]>([]);
  const [mediaTab, setMediaTab] = useState<
    "photos" | "videos" | "generated"
  >("photos");
  const [selectedVideo, setSelectedVideo] = useState<UploadedVideo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);
  const [photoActions, setPhotoActions] = useState<EventPhoto | null>(null);
  const [photoToDelete, setPhotoToDelete] = useState<EventPhoto | null>(null);
  const [deletingPhoto, setDeletingPhoto] = useState(false);
  const [downloadingPhoto, setDownloadingPhoto] = useState(false);
  const [updatingPhotoPreference, setUpdatingPhotoPreference] = useState(false);
  const [attempt, setAttempt] = useState(0);

  const updateSlideshowPreference = async (
    action: "approve" | "exclude"
  ) => {
    if (!id || !photoActions || updatingPhotoPreference) return;

    const selectedPhotoId = photoActions.id;
    setUpdatingPhotoPreference(true);
    try {
      const response = await apiFetch<SlideshowPreferenceResponse>(
        `/events/${id}/photos/${selectedPhotoId}/slideshow`,
        { action },
        "PATCH"
      );
      setPhotos((current) =>
        current.map((photo) =>
          photo.id === selectedPhotoId
            ? {
                ...photo,
                filterStatus: response.photo.filter_status,
                filterReason: response.photo.filter_reason,
                userApproved: isUserApproved(response.photo.user_approved),
              }
            : photo
        )
      );
      setPhotoActions(null);
      Alert.alert(
        action === "approve" ? "Photo Approved" : "Photo Excluded",
        response.message
      );
    } catch (caught) {
      Alert.alert(
        "Could Not Update Photo",
        caught instanceof Error ? caught.message : "Please try again."
      );
    } finally {
      setUpdatingPhotoPreference(false);
    }
  };

  const deletePhoto = async () => {
    if (!id || !photoToDelete || deletingPhoto) return;

    setDeletingPhoto(true);
    try {
      await apiFetch(
        `/events/${id}/photos/${photoToDelete.id}`,
        undefined,
        "DELETE"
      );
      setPhotos((current) =>
        current.filter((photo) => photo.id !== photoToDelete.id)
      );
      setPhotoTotal((current) => Math.max(0, current - 1));
      setPhotoOffset((current) => Math.max(0, current - 1));
      setLightboxIndex(null);
      setPhotoToDelete(null);
    } catch (caught) {
      Alert.alert(
        "Could Not Remove Photo",
        caught instanceof Error ? caught.message : "Please try again."
      );
    } finally {
      setDeletingPhoto(false);
    }
  };

  const downloadSelectedPhoto = async () => {
    if (!photoActions || downloadingPhoto) return;

    const selectedPhoto = photoActions;
    setDownloadingPhoto(true);
    try {
      await downloadPhoto(
        selectedPhoto.uri,
        getPhotoFileName(selectedPhoto)
      );
      setPhotoActions(null);
    } catch (caught) {
      Alert.alert(
        "Could Not Download Photo",
        caught instanceof Error ? caught.message : "Please try again."
      );
    } finally {
      setDownloadingPhoto(false);
    }
  };

  const downloadLightboxPhoto = async (photo: LightboxPhoto) => {
    const selectedPhoto = photos.find((item) => item.id === photo.id);
    if (!selectedPhoto) {
      throw new Error("This photo is no longer available.");
    }

    await downloadPhoto(
      selectedPhoto.uri,
      getPhotoFileName(selectedPhoto)
    );
  };

  useEffect(() => {
    if (!id) return;
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    setPhotos([]);
    setVideos([]);
    setPhotoOffset(0);
    setVideoOffset(0);
    setHasMorePhotos(false);
    setHasMoreVideos(false);

    (async () => {
      try {
        const [eventRes, mediaRes, generatedRes] = await Promise.all([
          apiFetch(`/events/${id}`, undefined, "GET", controller.signal),
          apiFetch<EventMediaResponse>(
            `/events/${id}/media?dataType=both&limit=${MEDIA_PAGE_SIZE}&offset=0`,
            undefined,
            "GET",
            controller.signal
          ),
          apiFetch<GeneratedVideosResponse>(
            `/events/${id}/generated-videos`,
            undefined,
            "GET",
            controller.signal
          ),
        ]);
        setEvent(eventRes.event);
        const rawPhotoCount = mediaRes.photo_count ?? mediaRes.photos?.length ?? 0;
        const rawVideoCount = mediaRes.video_count ?? mediaRes.videos?.length ?? 0;
        const reportedPhotoTotal = mediaRes.photo_total ?? rawPhotoCount;
        const reportedVideoTotal = mediaRes.video_total ?? rawVideoCount;
        const loadedPhotos = mapPhotos(mediaRes.photos ?? []);
        const loadedVideos = mapUploadedVideos(mediaRes.videos ?? []);

        setPhotos(loadedPhotos);
        setVideos(loadedVideos);
        setPhotoTotal(reportedPhotoTotal > 0 ? reportedPhotoTotal : rawPhotoCount);
        setVideoTotal(reportedVideoTotal > 0 ? reportedVideoTotal : rawVideoCount);
        setPhotoOffset(rawPhotoCount);
        setVideoOffset(rawVideoCount);
        setHasMorePhotos(
          mediaRes.has_more_photos === true ||
            (reportedPhotoTotal === 0 && rawPhotoCount === MEDIA_PAGE_SIZE)
        );
        setHasMoreVideos(
          mediaRes.has_more_videos === true ||
            (reportedVideoTotal === 0 && rawVideoCount === MEDIA_PAGE_SIZE)
        );
        const loadedGeneratedVideos = (generatedRes.videos ?? [])
          .filter(
            (video) =>
              video.status === "completed" &&
              Number.isInteger(video.gen_vid_id) &&
              video.gen_vid_id > 0
          )
          .map((video) => ({
            id: String(video.gen_vid_id),
            title:
              video.title ||
              video.file_name ||
              `Generated video ${video.gen_vid_id}`,
            durationSeconds: video.duration_seconds ?? null,
          }));
        setGeneratedVideos(loadedGeneratedVideos);
        if ((mediaRes.photos ?? []).length === 0) {
          setMediaTab(
            loadedVideos.length > 0
              ? "videos"
              : loadedGeneratedVideos.length > 0
                ? "generated"
                : "photos"
          );
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

  const loadMorePhotos = async () => {
    if (!id || loadingMorePhotosRef.current || !hasMorePhotos) return;

    loadingMorePhotosRef.current = true;
    setLoadingMorePhotos(true);
    try {
      const response = await apiFetch<EventMediaResponse>(
        `/events/${id}/media?dataType=photos&limit=${MEDIA_PAGE_SIZE}&offset=${photoOffset}`
      );
      const rawCount = response.photo_count ?? response.photos?.length ?? 0;
      const loaded = mapPhotos(response.photos ?? []);

      setPhotos((current) => dedupePhotos([...current, ...loaded]));
      setPhotoOffset((current) => current + rawCount);
      if ((response.photo_total ?? 0) > 0) {
        setPhotoTotal(response.photo_total as number);
      }
      setHasMorePhotos(
        response.has_more_photos === true ||
          ((response.photo_total ?? 0) === 0 && rawCount === MEDIA_PAGE_SIZE)
      );
    } catch (caught) {
      Alert.alert(
        "Could Not Load More Photos",
        caught instanceof Error ? caught.message : "Please try again."
      );
    } finally {
      loadingMorePhotosRef.current = false;
      setLoadingMorePhotos(false);
    }
  };

  const loadMoreVideos = async () => {
    if (!id || loadingMoreVideosRef.current || !hasMoreVideos) return;

    loadingMoreVideosRef.current = true;
    setLoadingMoreVideos(true);
    try {
      const response = await apiFetch<EventMediaResponse>(
        `/events/${id}/media?dataType=videos&limit=${MEDIA_PAGE_SIZE}&offset=${videoOffset}`
      );
      const rawCount = response.video_count ?? response.videos?.length ?? 0;
      const loaded = mapUploadedVideos(response.videos ?? []);

      setVideos((current) => {
        const existing = new Set(current.map((video) => video.id));
        return [...current, ...loaded.filter((video) => !existing.has(video.id))];
      });
      setVideoOffset((current) => current + rawCount);
      if ((response.video_total ?? 0) > 0) {
        setVideoTotal(response.video_total as number);
      }
      setHasMoreVideos(
        response.has_more_videos === true ||
          ((response.video_total ?? 0) === 0 && rawCount === MEDIA_PAGE_SIZE)
      );
    } catch (caught) {
      Alert.alert(
        "Could Not Load More Videos",
        caught instanceof Error ? caught.message : "Please try again."
      );
    } finally {
      loadingMoreVideosRef.current = false;
      setLoadingMoreVideos(false);
    }
  };

  const dateLabel = useMemo(() => {
    if (!event?.event_date) return "";
    const [y, m, d] = event.event_date.slice(0, 10).split("-").map(Number);
    return new Date(y, m - 1, d).toLocaleDateString();
  }, [event?.event_date]);

  const selectedPhotoNeedsApproval = Boolean(
    photoActions?.filterStatus?.toLowerCase() === "rejected" &&
      !photoActions.userApproved &&
      hasQualityFilterRejection(photoActions.filterReason)
  );
  const selectedPhotoIsUserExcluded = Boolean(
    photoActions?.filterReason
      ?.split(",")
      .some((reason) => reason.trim() === "user_excluded") &&
      !photoActions?.userApproved
  );

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
            {photoTotal} photo{photoTotal !== 1 ? "s" : ""}
            {videoTotal > 0 ? ` · ${videoTotal} video${videoTotal !== 1 ? "s" : ""}` : ""}
            {generatedVideos.length > 0
              ? ` · ${generatedVideos.length} generated`
              : ""}
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
                Photos ({photoTotal})
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
                Videos ({videoTotal})
              </Text>
            </TouchableOpacity>
            {generatedVideos.length > 0 && (
              <TouchableOpacity
                onPress={() => setMediaTab("generated")}
                style={[
                  s.tab,
                  mediaTab === "generated" && {
                    backgroundColor: c.accentStrong,
                  },
                ]}
              >
                <Ionicons
                  name="sparkles-outline"
                  size={18}
                  color={mediaTab === "generated" ? "#fff" : c.textMuted}
                />
                <Text
                  style={[
                    s.tabText,
                    {
                      color:
                        mediaTab === "generated" ? "#fff" : c.textMuted,
                    },
                  ]}
                >
                  Generated ({generatedVideos.length})
                </Text>
              </TouchableOpacity>
            )}
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
                onEndReached={() => void loadMorePhotos()}
                onEndReachedThreshold={0.4}
                ListFooterComponent={
                  loadingMorePhotos ? (
                    <ActivityIndicator
                      color={c.accent}
                      style={{ marginVertical: 18 }}
                    />
                  ) : null
                }
                renderItem={({ item, index }) => (
                  <View
                    style={{
                      width: photoCellSize,
                      height: photoCellSize,
                      padding: 1,
                    }}
                  >
                    <TouchableOpacity
                      activeOpacity={0.85}
                      onPress={() => setLightboxIndex(index)}
                      style={StyleSheet.absoluteFill}
                    >
                      <Image
                        source={{ uri: item.uri }}
                        style={s.cellImage}
                        resizeMode="cover"
                        blurRadius={item.isSensitive ? 28 : 0}
                      />
                      {item.isSensitive ? (
                        <View style={s.sensitiveOverlay} pointerEvents="none">
                          <Ionicons name="warning" size={18} color="#FCA5A5" />
                          <Text style={s.sensitiveText}>Nudity warning</Text>
                          <Text style={s.sensitiveHint}>Tap to view</Text>
                        </View>
                      ) : null}
                    </TouchableOpacity>
                    <TouchableOpacity
                      style={s.photoMenuButton}
                      accessibilityLabel="Photo options"
                      onPress={() => setPhotoActions(item)}
                    >
                      <Ionicons name="ellipsis-horizontal" size={20} color="#fff" />
                    </TouchableOpacity>
                  </View>
                )}
              />
            )
          ) : mediaTab === "videos" ? (
            <FlatList
              key="videos"
              data={videos}
              keyExtractor={(item) => item.id}
              contentContainerStyle={[
                s.videoList,
                videos.length === 0 && s.emptyList,
              ]}
              onEndReached={() => void loadMoreVideos()}
              onEndReachedThreshold={0.4}
              ListFooterComponent={
                loadingMoreVideos ? (
                  <ActivityIndicator
                    color={c.accent}
                    style={{ marginVertical: 18 }}
                  />
                ) : null
              }
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
          ) : (
            <FlatList
              key="generated"
              data={generatedVideos}
              keyExtractor={(item) => item.id}
              contentContainerStyle={s.videoList}
              renderItem={({ item }) => (
                <TouchableOpacity
                  activeOpacity={0.85}
                  onPress={() =>
                    router.push(`/events/${id}/videos/${item.id}`)
                  }
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
                    <Ionicons name="sparkles" size={24} color="#fff" />
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

      {event && id ? (
        <View style={s.floatingActions}>
          <TouchableOpacity
            style={[s.floatingButton, s.chatButton]}
            accessibilityLabel="Open video assistant for this event"
            onPress={() =>
              router.push({
                pathname: "/chatbot",
                params: { eventId: id },
              })
            }
          >
            <Ionicons name="chatbubble-ellipses" size={21} color="#fff" />
          </TouchableOpacity>
          <TouchableOpacity
            style={s.floatingButton}
            accessibilityLabel="Upload photos to this event"
            onPress={() => {
              setCurrentEvent(event.event_id, event.name);
              router.push("/upload");
            }}
          >
            <Ionicons name="cloud-upload" size={22} color="#fff" />
          </TouchableOpacity>
        </View>
      ) : null}

      {lightboxIndex !== null && (
        <Lightbox
          photos={photos}
          startIndex={lightboxIndex}
          totalCount={photoTotal}
          hasMore={hasMorePhotos}
          onLoadMore={() => void loadMorePhotos()}
          onDownload={downloadLightboxPhoto}
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
      <Modal
        visible={photoActions !== null}
        transparent
        animationType="fade"
        onRequestClose={() =>
          !updatingPhotoPreference && !downloadingPhoto && setPhotoActions(null)
        }
      >
        <View style={s.actionBackdrop}>
          <Pressable
            style={StyleSheet.absoluteFill}
            onPress={() =>
              !updatingPhotoPreference &&
              !downloadingPhoto &&
              setPhotoActions(null)
            }
          />
          <View style={s.actionSheet}>
            <View style={s.actionHeader}>
              <View>
                <Text style={s.actionTitle}>Photo options</Text>
                {photoActions?.filterStatus ? (
                  <Text style={s.actionStatus}>
                    Filter: {photoActions.filterStatus}
                    {photoActions.userApproved ? " · user approved" : ""}
                  </Text>
                ) : null}
              </View>
              {updatingPhotoPreference || downloadingPhoto ? (
                <ActivityIndicator color={c.accent} />
              ) : null}
            </View>

            {selectedPhotoNeedsApproval ? (
              <TouchableOpacity
                style={s.actionRow}
                disabled={updatingPhotoPreference || downloadingPhoto}
                onPress={() => void updateSlideshowPreference("approve")}
              >
                <View style={[s.actionIcon, { backgroundColor: c.bg }]}>
                  <Ionicons
                    name="checkmark-circle-outline"
                    size={22}
                    color={c.accent}
                  />
                </View>
                <View style={s.actionCopy}>
                  <Text style={s.actionLabel}>Approve for slideshow</Text>
                  <Text style={s.actionDescription}>
                    Override the automatic photo rejection.
                  </Text>
                </View>
              </TouchableOpacity>
            ) : null}

            <TouchableOpacity
              style={s.actionRow}
              disabled={
                updatingPhotoPreference ||
                downloadingPhoto ||
                selectedPhotoIsUserExcluded
              }
              onPress={() => void updateSlideshowPreference("exclude")}
            >
              <View style={[s.actionIcon, { backgroundColor: c.bg }]}>
                <Ionicons
                  name="remove-circle-outline"
                  size={22}
                  color={c.textMuted}
                />
              </View>
              <View style={s.actionCopy}>
                <Text style={s.actionLabel}>
                  {selectedPhotoIsUserExcluded
                    ? "Excluded from slideshow"
                    : "Don’t include in slideshow"}
                </Text>
              </View>
            </TouchableOpacity>

            <TouchableOpacity
              style={s.actionRow}
              disabled={updatingPhotoPreference || downloadingPhoto}
              onPress={() => void downloadSelectedPhoto()}
            >
              <View style={[s.actionIcon, { backgroundColor: c.bg }]}>
                <Ionicons
                  name="download-outline"
                  size={22}
                  color={c.accent}
                />
              </View>
              <View style={s.actionCopy}>
                <Text style={s.actionLabel}>
                  {downloadingPhoto ? "Downloading…" : "Download photo"}
                </Text>
              </View>
            </TouchableOpacity>

            <TouchableOpacity
              style={s.actionRow}
              disabled={updatingPhotoPreference || downloadingPhoto}
              onPress={() => {
                const selected = photoActions;
                setPhotoActions(null);
                setPhotoToDelete(selected);
              }}
            >
              <View style={[s.actionIcon, { backgroundColor: c.bg }]}>
                <Ionicons name="trash-outline" size={22} color={c.danger} />
              </View>
              <View style={s.actionCopy}>
                <Text style={[s.actionLabel, { color: c.danger }]}>Delete</Text>
              </View>
            </TouchableOpacity>

            <TouchableOpacity
              style={s.actionCancel}
              disabled={updatingPhotoPreference || downloadingPhoto}
              onPress={() => setPhotoActions(null)}
            >
              <Text style={s.actionCancelText}>Cancel</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
      <Modal
        visible={photoToDelete !== null}
        transparent
        animationType="fade"
        onRequestClose={() => !deletingPhoto && setPhotoToDelete(null)}
      >
        <View style={s.deleteBackdrop}>
          <Pressable
            style={StyleSheet.absoluteFill}
            onPress={() => !deletingPhoto && setPhotoToDelete(null)}
          />
          <View style={s.deleteCard}>
            <View style={s.deleteIcon}>
              <Ionicons name="trash-outline" size={25} color={c.danger} />
            </View>
            <Text style={s.deleteTitle}>Remove this photo?</Text>
            <Text style={s.deleteCopy}>
              It will be hidden from the gallery. The original file will not be deleted.
            </Text>
            <View style={s.deleteActions}>
              <TouchableOpacity
                style={s.cancelDeleteButton}
                disabled={deletingPhoto}
                onPress={() => setPhotoToDelete(null)}
              >
                <Text style={s.cancelDeleteText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={s.confirmDeleteButton}
                disabled={deletingPhoto}
                onPress={() => void deletePhoto()}
              >
                {deletingPhoto ? (
                  <ActivityIndicator size="small" color="#fff" />
                ) : (
                  <Text style={s.confirmDeleteText}>Remove</Text>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
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
      flexWrap: "wrap",
      justifyContent: "center",
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
    sensitiveOverlay: {
      position: "absolute",
      top: 1,
      right: 1,
      bottom: 1,
      left: 1,
      alignItems: "center",
      justifyContent: "center",
      gap: 5,
      backgroundColor: "rgba(5,8,16,0.22)",
      borderRadius: 4,
    },
    sensitiveText: { color: "#fff", fontSize: 11, fontWeight: "800" },
    sensitiveHint: { color: "rgba(255,255,255,0.78)", fontSize: 10, fontWeight: "600" },
    photoMenuButton: {
      position: "absolute",
      top: 7,
      right: 7,
      zIndex: 4,
      width: 32,
      height: 32,
      borderRadius: 10,
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: "rgba(5,8,16,0.82)",
      borderWidth: 1,
      borderColor: "rgba(255,255,255,0.35)",
    },
    actionBackdrop: {
      flex: 1,
      justifyContent: "flex-end",
      alignItems: "center",
      backgroundColor: "rgba(5,8,16,0.66)",
    },
    actionSheet: {
      width: "100%",
      maxWidth: 520,
      paddingHorizontal: 18,
      paddingTop: 18,
      paddingBottom: Platform.OS === "ios" ? 34 : 20,
      borderTopLeftRadius: 22,
      borderTopRightRadius: 22,
      backgroundColor: c.surface,
      borderWidth: 1,
      borderColor: c.border,
    },
    actionHeader: {
      minHeight: 48,
      flexDirection: "row",
      justifyContent: "space-between",
      alignItems: "center",
      marginBottom: 8,
    },
    actionTitle: { color: c.textBright, fontSize: 20, fontWeight: "800" },
    actionStatus: { color: c.textMuted, fontSize: 12, marginTop: 3 },
    actionRow: {
      minHeight: 68,
      flexDirection: "row",
      alignItems: "center",
      gap: 12,
      paddingVertical: 10,
      borderBottomWidth: StyleSheet.hairlineWidth,
      borderBottomColor: c.border,
    },
    actionIcon: {
      width: 42,
      height: 42,
      borderRadius: 13,
      alignItems: "center",
      justifyContent: "center",
    },
    actionCopy: { flex: 1 },
    actionLabel: { color: c.textPrimary, fontSize: 15, fontWeight: "700" },
    actionDescription: {
      color: c.textMuted,
      fontSize: 12,
      lineHeight: 17,
      marginTop: 2,
    },
    actionCancel: {
      minHeight: 46,
      alignItems: "center",
      justifyContent: "center",
      marginTop: 12,
      borderRadius: 12,
      backgroundColor: c.bg,
      borderWidth: 1,
      borderColor: c.border,
    },
    actionCancelText: { color: c.textPrimary, fontSize: 14, fontWeight: "700" },
    deleteBackdrop: {
      flex: 1,
      alignItems: "center",
      justifyContent: "center",
      padding: 24,
      backgroundColor: "rgba(5,8,16,0.76)",
    },
    deleteCard: {
      width: "100%",
      maxWidth: 420,
      borderRadius: 20,
      padding: 24,
      backgroundColor: c.surface,
      borderWidth: 1,
      borderColor: c.border,
    },
    deleteIcon: {
      width: 48,
      height: 48,
      borderRadius: 15,
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: c.bg,
      marginBottom: 15,
    },
    deleteTitle: { color: c.textBright, fontSize: 21, fontWeight: "800" },
    deleteCopy: { color: c.textMuted, fontSize: 14, lineHeight: 20, marginTop: 7 },
    deleteActions: { flexDirection: "row", gap: 10, marginTop: 22 },
    cancelDeleteButton: {
      flex: 1,
      minHeight: 46,
      alignItems: "center",
      justifyContent: "center",
      borderRadius: 12,
      borderWidth: 1,
      borderColor: c.border,
    },
    cancelDeleteText: { color: c.textPrimary, fontWeight: "700" },
    confirmDeleteButton: {
      flex: 1,
      minHeight: 46,
      alignItems: "center",
      justifyContent: "center",
      borderRadius: 12,
      backgroundColor: c.danger,
    },
    confirmDeleteText: { color: "#fff", fontWeight: "800" },
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
    floatingActions: {
      position: "absolute",
      right: 18,
      bottom: 20,
      alignItems: "center",
      gap: 10,
    },
    floatingButton: {
      width: 56,
      height: 56,
      borderRadius: 18,
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: c.accentStrong,
      borderWidth: 1,
      borderColor: c.accent,
      shadowColor: "#000",
      shadowOffset: { width: 0, height: 6 },
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
