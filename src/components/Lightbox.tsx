import { Ionicons } from "@expo/vector-icons";
import { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Image,
  Modal,
  Platform,
  StatusBar,
  StyleSheet,
  Text,
  TouchableOpacity,
  useWindowDimensions,
  View,
} from "react-native";

export type LightboxPhoto = {
  id: string;
  uri: string;
  isSensitive?: boolean;
};

export default function Lightbox({
  photos,
  startIndex,
  totalCount,
  hasMore = false,
  onLoadMore,
  onDownload,
  onClose,
}: {
  photos: LightboxPhoto[];
  startIndex: number;
  totalCount?: number;
  hasMore?: boolean;
  onLoadMore?: () => void;
  onDownload?: (photo: LightboxPhoto) => Promise<void>;
  onClose: () => void;
}) {
  const { width: viewportWidth, height: viewportHeight } =
    useWindowDimensions();
  const listRef = useRef<FlatList<LightboxPhoto>>(null);
  const [current, setCurrent] = useState(startIndex);
  const [revealedPhotoIds, setRevealedPhotoIds] = useState<Set<string>>(
    () => new Set()
  );
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const setPhotoRevealed = (photoId: string, revealed: boolean) => {
    setRevealedPhotoIds((previous) => {
      const next = new Set(previous);
      if (revealed) next.add(photoId);
      else next.delete(photoId);
      return next;
    });
  };

  const goToPhoto = (index: number) => {
    if (index < 0 || index >= photos.length) return;
    setCurrent(index);
    if (hasMore && index >= photos.length - 6) onLoadMore?.();
    listRef.current?.scrollToIndex({ index, animated: true });
  };

  const downloadCurrentPhoto = async () => {
    const photo = photos[current];
    if (!photo || !onDownload || downloading) return;

    setDownloading(true);
    setDownloadError(null);
    try {
      await onDownload(photo);
    } catch (caught) {
      setDownloadError(
        caught instanceof Error ? caught.message : "The photo could not be downloaded."
      );
    } finally {
      setDownloading(false);
    }
  };

  useEffect(() => {
    if (hasMore && current >= photos.length - 6) onLoadMore?.();
  }, [current, hasMore, onLoadMore, photos.length]);

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      listRef.current?.scrollToIndex({ index: current, animated: false });
    });

    return () => cancelAnimationFrame(frame);
  }, [viewportWidth]);

  return (
    <Modal visible animationType="fade" statusBarTranslucent>
      <View style={lb.container}>
        <StatusBar hidden />
        <TouchableOpacity
          style={lb.closeBtn}
          onPress={onClose}
          accessibilityLabel="Close photo viewer"
        >
          <Ionicons name="close" size={26} color="#F0F4FF" />
        </TouchableOpacity>
        {onDownload ? (
          <TouchableOpacity
            style={lb.downloadBtn}
            onPress={() => void downloadCurrentPhoto()}
            disabled={downloading}
            accessibilityRole="button"
            accessibilityLabel="Download photo"
          >
            {downloading ? (
              <ActivityIndicator size="small" color="#F0F4FF" />
            ) : (
              <Ionicons name="download-outline" size={23} color="#F0F4FF" />
            )}
          </TouchableOpacity>
        ) : null}
        <View style={lb.counter}>
          <Text style={lb.counterText}>
            {current + 1} / {totalCount ?? photos.length}
          </Text>
        </View>
        <FlatList
          ref={listRef}
          data={photos}
          horizontal
          pagingEnabled
          showsHorizontalScrollIndicator={false}
          initialScrollIndex={startIndex}
          getItemLayout={(_, index) => ({
            length: viewportWidth,
            offset: viewportWidth * index,
            index,
          })}
          onMomentumScrollEnd={(e) => {
            const nextIndex = Math.round(
              e.nativeEvent.contentOffset.x / viewportWidth
            );
            setCurrent(nextIndex);
            if (hasMore && nextIndex >= photos.length - 6) onLoadMore?.();
          }}
          onScrollToIndexFailed={({ index }) => {
            listRef.current?.scrollToOffset({
              offset: index * viewportWidth,
              animated: false,
            });
          }}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => {
            const isBlurred =
              Boolean(item.isSensitive) && !revealedPhotoIds.has(item.id);

            return (
              <View
                style={[
                  lb.slide,
                  { width: viewportWidth, height: viewportHeight },
                ]}
              >
                <Image
                  source={{ uri: item.uri }}
                  style={{
                    width: viewportWidth,
                    height: Math.max(viewportHeight - 112, 1),
                  }}
                  resizeMode="contain"
                  blurRadius={isBlurred ? 40 : 0}
                />
                {isBlurred ? (
                  <TouchableOpacity
                    style={lb.sensitiveNotice}
                    activeOpacity={0.85}
                    onPress={() => setPhotoRevealed(item.id, true)}
                    accessibilityRole="button"
                    accessibilityLabel="Nudity detected. View photo"
                  >
                    <Ionicons name="warning" size={22} color="#FCA5A5" />
                    <View>
                      <Text style={lb.warningText}>Nudity detected</Text>
                      <Text style={lb.sensitiveText}>Tap to view photo</Text>
                    </View>
                  </TouchableOpacity>
                ) : item.isSensitive ? (
                  <TouchableOpacity
                    style={lb.reblurButton}
                    activeOpacity={0.85}
                    onPress={() => setPhotoRevealed(item.id, false)}
                    accessibilityRole="button"
                    accessibilityLabel="Blur photo again"
                  >
                    <Ionicons name="eye-off" size={17} color="#F0F4FF" />
                    <Text style={lb.reblurText}>Blur again</Text>
                  </TouchableOpacity>
                ) : null}
              </View>
            );
          }}
        />
        {Platform.OS === "web" && current > 0 ? (
          <TouchableOpacity
            style={[lb.arrowButton, lb.previousButton]}
            onPress={() => goToPhoto(current - 1)}
            accessibilityRole="button"
            accessibilityLabel="Previous photo"
          >
            <Ionicons name="chevron-back" size={32} color="#F0F4FF" />
          </TouchableOpacity>
        ) : null}
        {Platform.OS === "web" && current < photos.length - 1 ? (
          <TouchableOpacity
            style={[lb.arrowButton, lb.nextButton]}
            onPress={() => goToPhoto(current + 1)}
            accessibilityRole="button"
            accessibilityLabel="Next photo"
          >
            <Ionicons name="chevron-forward" size={32} color="#F0F4FF" />
          </TouchableOpacity>
        ) : null}
        {downloadError ? (
          <View style={lb.downloadError}>
            <Text style={lb.downloadErrorText}>{downloadError}</Text>
          </View>
        ) : null}
        {photos.length <= 12 ? (
          <View style={lb.dots}>
            {photos.map((photo, i) => (
              <View
                key={photo.id}
                style={[lb.dot, i === current && lb.dotActive]}
              />
            ))}
          </View>
        ) : null}
      </View>
    </Modal>
  );
}

const lb = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#050810", justifyContent: "center" },
  closeBtn: {
    position: "absolute",
    top: Platform.OS === "ios" ? 56 : 36,
    right: 20,
    zIndex: 10,
    backgroundColor: "rgba(0,0,0,0.5)",
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: "center",
    justifyContent: "center",
  },
  downloadBtn: {
    position: "absolute",
    top: Platform.OS === "ios" ? 56 : 36,
    right: 72,
    zIndex: 10,
    backgroundColor: "rgba(0,0,0,0.5)",
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: "center",
    justifyContent: "center",
  },
  counter: {
    position: "absolute",
    top: Platform.OS === "ios" ? 60 : 40,
    left: 20,
    zIndex: 10,
    backgroundColor: "rgba(0,0,0,0.5)",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
  },
  counterText: { color: "#F0F4FF", fontSize: 13, fontWeight: "600" },
  slide: { alignItems: "center", justifyContent: "center" },
  arrowButton: {
    position: "absolute",
    top: "50%",
    zIndex: 12,
    width: 52,
    height: 64,
    marginTop: -32,
    borderRadius: 26,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(5,8,16,0.68)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.18)",
  },
  previousButton: { left: 18 },
  nextButton: { right: 18 },
  sensitiveNotice: {
    position: "absolute",
    alignSelf: "center",
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    backgroundColor: "rgba(69,10,10,0.92)",
    borderWidth: 1,
    borderColor: "rgba(252,165,165,0.55)",
    paddingHorizontal: 18,
    paddingVertical: 12,
    borderRadius: 16,
  },
  warningText: { color: "#FCA5A5", fontSize: 14, fontWeight: "800" },
  sensitiveText: { color: "#F0F4FF", fontSize: 12, fontWeight: "600", marginTop: 2 },
  reblurButton: {
    position: "absolute",
    bottom: 18,
    alignSelf: "center",
    flexDirection: "row",
    alignItems: "center",
    gap: 7,
    backgroundColor: "rgba(5,8,16,0.78)",
    paddingHorizontal: 14,
    paddingVertical: 9,
    borderRadius: 18,
  },
  reblurText: { color: "#F0F4FF", fontSize: 12, fontWeight: "700" },
  dots: {
    position: "absolute",
    bottom: 60,
    left: 0,
    right: 0,
    flexDirection: "row",
    justifyContent: "center",
    gap: 6,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: "rgba(255,255,255,0.3)",
  },
  dotActive: { backgroundColor: "#3B82F6", width: 18 },
  downloadError: {
    position: "absolute",
    bottom: 28,
    alignSelf: "center",
    maxWidth: 420,
    marginHorizontal: 20,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 12,
    backgroundColor: "rgba(127,29,29,0.94)",
  },
  downloadErrorText: { color: "#FEE2E2", fontSize: 13, fontWeight: "600" },
});
