import { Ionicons } from "@expo/vector-icons";
import { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Dimensions,
  FlatList,
  Image,
  Modal,
  Platform,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { API_URL } from "@/lib/api";
import { ThemeColors } from "@/theme/colors";
import { useTheme } from "@/theme/ThemeContext";

const { width: SCREEN_WIDTH } = Dimensions.get("window");
const CARD_WIDTH = (SCREEN_WIDTH - 48) / 2;

type Photo = { id: string; uri: string };
type Gallery = {
  id: string;
  title: string;
  date: string;
  photoCount: number;
  coverColor: string;
  accentColor: string;
  photos: Photo[];
};

// Photo Lightbox (media surface — always dark)
function Lightbox({
  photos,
  startIndex,
  onClose,
}: {
  photos: Photo[];
  startIndex: number;
  onClose: () => void;
}) {
  const [current, setCurrent] = useState(startIndex);

  return (
    <Modal visible animationType="fade" statusBarTranslucent>
      <View style={lb.container}>
        <StatusBar hidden />
        <TouchableOpacity style={lb.closeBtn} onPress={onClose}>
          <Ionicons name="close" size={26} color="#F0F4FF" />
        </TouchableOpacity>
        <View style={lb.counter}>
          <Text style={lb.counterText}>
            {current + 1} / {photos.length}
          </Text>
        </View>
        <FlatList
          data={photos}
          horizontal
          pagingEnabled
          showsHorizontalScrollIndicator={false}
          initialScrollIndex={startIndex}
          getItemLayout={(_, index) => ({
            length: SCREEN_WIDTH,
            offset: SCREEN_WIDTH * index,
            index,
          })}
          onMomentumScrollEnd={(e) => {
            const idx = Math.round(
              e.nativeEvent.contentOffset.x / SCREEN_WIDTH
            );
            setCurrent(idx);
          }}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <View style={{ width: SCREEN_WIDTH, justifyContent: "center" }}>
              <Image
                source={{ uri: item.uri }}
                style={lb.photo}
                resizeMode="contain"
              />
            </View>
          )}
        />
        <View style={lb.dots}>
          {photos.map((_, i) => (
            <View key={i} style={[lb.dot, i === current && lb.dotActive]} />
          ))}
        </View>
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
  photo: { width: SCREEN_WIDTH, height: SCREEN_WIDTH },
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
});

//Gallery Detail Modal
function GalleryDetail({
  gallery,
  onClose,
}: {
  gallery: Gallery;
  onClose: () => void;
}) {
  const { colors: c } = useTheme();
  const gd = useMemo(() => makeDetailStyles(c), [c]);
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);
  const numCols = 3;
  const cellSize = (SCREEN_WIDTH - 4) / numCols;

  return (
    <Modal visible animationType="slide">
      <View style={gd.container}>
        <StatusBar barStyle={c.statusBar} />
        <SafeAreaView>
          <View style={gd.header}>
            <TouchableOpacity onPress={onClose} style={gd.backBtn}>
              <Ionicons name="chevron-back" size={24} color={c.textBright} />
            </TouchableOpacity>
            <View style={gd.headerText}>
              <Text style={gd.title}>{gallery.title}</Text>
              <Text style={gd.meta}>
                {gallery.date} · {gallery.photoCount} photos
              </Text>
            </View>
            <View
              style={[gd.accentDot, { backgroundColor: gallery.accentColor }]}
            />
          </View>
        </SafeAreaView>
        <View style={[gd.divider, { backgroundColor: gallery.accentColor }]} />
        <FlatList
          data={gallery.photos}
          numColumns={numCols}
          keyExtractor={(item) => item.id}
          contentContainerStyle={gd.grid}
          renderItem={({ item, index }) => (
            <TouchableOpacity
              activeOpacity={0.85}
              onPress={() => setLightboxIndex(index)}
              style={[gd.cell, { width: cellSize, height: cellSize }]}
            >
              <Image
                source={{ uri: item.uri }}
                style={gd.cellImage}
                resizeMode="cover"
              />
              <View style={gd.cellOverlay} />
            </TouchableOpacity>
          )}
        />
        {lightboxIndex !== null && (
          <Lightbox
            photos={gallery.photos}
            startIndex={lightboxIndex}
            onClose={() => setLightboxIndex(null)}
          />
        )}
      </View>
    </Modal>
  );
}

const makeDetailStyles = (c: ThemeColors) =>
  StyleSheet.create({
    container: { flex: 1, backgroundColor: c.bg },
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
      alignItems: "center",
      justifyContent: "center",
    },
    headerText: { flex: 1 },
    title: {
      fontSize: 18,
      fontWeight: "800",
      color: c.textBright,
      fontFamily: Platform.OS === "ios" ? "Georgia" : "serif",
      letterSpacing: -0.4,
    },
    meta: { fontSize: 12, color: c.textMuted, marginTop: 2 },
    accentDot: { width: 10, height: 10, borderRadius: 5 },
    divider: {
      height: 2,
      marginHorizontal: 16,
      borderRadius: 2,
      opacity: 0.5,
      marginBottom: 2,
    },
    grid: { gap: 2 },
    cell: { overflow: "hidden" },
    cellImage: { width: "100%", height: "100%" },
    cellOverlay: {
      ...StyleSheet.absoluteFillObject,
      backgroundColor: "rgba(13,17,23,0.1)",
    },
  });

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
        <Image
          source={{ uri: gallery.photos[0]?.uri }}
          style={gc.coverImage}
          resizeMode="cover"
        />
        <View style={[gc.badge, { backgroundColor: gallery.accentColor }]}>
          <Ionicons name="images" size={10} color="#fff" />
          <Text style={gc.badgeText}>{gallery.photoCount}</Text>
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
    badge: {
      position: "absolute",
      top: 8,
      right: 8,
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
  const [selectedGallery, setSelectedGallery] = useState<Gallery | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    (async () => {
      try {
        const response = await fetch(`${API_URL}/events`, { signal: controller.signal });
        if (!response.ok) throw new Error("Failed to fetch galleries");
        setGalleries(await response.json());
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
                  onPress={() => setSelectedGallery(gallery)}
                />
              ))}
            </View>
          </ScrollView>
        )}

        {selectedGallery && (
          <GalleryDetail
            gallery={selectedGallery}
            onClose={() => setSelectedGallery(null)}
          />
        )}
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
  });
