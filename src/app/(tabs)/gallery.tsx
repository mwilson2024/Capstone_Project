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

  useEffect(() => {
    const controller = new AbortController();

    (async () => {
      try {
        const data = await apiFetch("/events", undefined, "GET", controller.signal);
        setGalleries(data);
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
                  onPress={() => router.push(`/event/${gallery.id}`)}
                />
              ))}
            </View>
          </ScrollView>
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
