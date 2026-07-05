import { Ionicons } from "@expo/vector-icons";
import {
  CameraType,
  CameraView,
  FlashMode,
  useCameraPermissions,
} from "expo-camera";
import * as MediaLibrary from "expo-media-library";
import { useCallback, useRef, useState } from "react";
import {
  Alert,
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

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get("window");

type CapturedPhoto = {
  id: string;
  uri: string;
  timestamp: number;
};

//Permission Gate
function PermissionScreen({ onRequest }: { onRequest: () => void }) {
  return (
    <View style={perm.container}>
      <View style={perm.iconRing}>
        <Ionicons name="camera" size={40} color="#3B82F6" />
      </View>
      <Text style={perm.title}>Camera Access</Text>
      <Text style={perm.body}>
        Allow access to your camera to take photos for your event galleries.
      </Text>
      <TouchableOpacity style={perm.btn} onPress={onRequest} activeOpacity={0.85}>
        <Text style={perm.btnText}>Grant Access</Text>
      </TouchableOpacity>
    </View>
  );
}

const perm = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0D1117",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 40,
  },
  iconRing: {
    width: 90,
    height: 90,
    borderRadius: 45,
    backgroundColor: "rgba(59,130,246,0.12)",
    borderWidth: 1.5,
    borderColor: "#1E3A6A",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 28,
  },
  title: {
    fontSize: 26,
    fontWeight: "800",
    color: "#F0F4FF",
    letterSpacing: -0.6,
    fontFamily: Platform.OS === "ios" ? "Georgia" : "serif",
    marginBottom: 12,
    textAlign: "center",
  },
  body: {
    fontSize: 15,
    color: "#5A6A85",
    textAlign: "center",
    lineHeight: 22,
    marginBottom: 36,
  },
  btn: {
    backgroundColor: "#2563EB",
    borderRadius: 14,
    paddingHorizontal: 40,
    paddingVertical: 16,
    shadowColor: "#2563EB",
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.4,
    shadowRadius: 14,
    elevation: 8,
  },
  btnText: {
    color: "#fff",
    fontSize: 15,
    fontWeight: "700",
    letterSpacing: 0.5,
  },
});

//Photo Preview Modal
function PhotoPreview({
  photo,
  onDiscard,
  onSave,
}: {
  photo: CapturedPhoto;
  onDiscard: () => void;
  onSave: () => void;
}) {
  return (
    <Modal visible animationType="fade" statusBarTranslucent>
      <View style={preview.container}>
        <StatusBar hidden />
        <Image
          source={{ uri: photo.uri }}
          style={preview.image}
          resizeMode="contain"
        />
        
        <View style={preview.topBar}>
          <TouchableOpacity style={preview.iconBtn} onPress={onDiscard}>
            <Ionicons name="close" size={24} color="#F0F4FF" />
          </TouchableOpacity>
          <Text style={preview.label}>Preview</Text>
          <View style={{ width: 40 }} />
        </View>

        <View style={preview.bottomBar}>
          <TouchableOpacity style={preview.discardBtn} onPress={onDiscard} activeOpacity={0.8}>
            <Ionicons name="trash-outline" size={20} color="#F87171" />
            <Text style={preview.discardText}>Discard</Text>
          </TouchableOpacity>
          <TouchableOpacity style={preview.saveBtn} onPress={onSave} activeOpacity={0.85}>
            <Ionicons name="download-outline" size={20} color="#fff" />
            <Text style={preview.saveText}>Save Photo</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}

const preview = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#050810" },
  image: { width: SCREEN_WIDTH, height: SCREEN_HEIGHT },
  topBar: {
    position: "absolute",
    top: Platform.OS === "ios" ? 56 : 36,
    left: 0,
    right: 0,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
  },
  iconBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "rgba(0,0,0,0.5)",
    alignItems: "center",
    justifyContent: "center",
  },
  label: {
    color: "#F0F4FF",
    fontSize: 16,
    fontWeight: "600",
    letterSpacing: 0.3,
  },
  bottomBar: {
    position: "absolute",
    bottom: Platform.OS === "ios" ? 44 : 24,
    left: 20,
    right: 20,
    flexDirection: "row",
    gap: 12,
  },
  discardBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: "rgba(248,113,113,0.12)",
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "rgba(248,113,113,0.3)",
    paddingVertical: 14,
  },
  discardText: {
    color: "#F87171",
    fontSize: 15,
    fontWeight: "600",
  },
  saveBtn: {
    flex: 2,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: "#2563EB",
    borderRadius: 14,
    paddingVertical: 14,
    shadowColor: "#2563EB",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4,
    shadowRadius: 10,
    elevation: 6,
  },
  saveText: {
    color: "#fff",
    fontSize: 15,
    fontWeight: "700",
  },
});

// Thumbnail Strip
function ThumbnailStrip({
  photos,
  onTap,
}: {
  photos: CapturedPhoto[];
  onTap: (photo: CapturedPhoto) => void;
}) {
  if (photos.length === 0) return null;
  return (
    <FlatList
      data={[...photos].reverse()}
      horizontal
      showsHorizontalScrollIndicator={false}
      keyExtractor={(item) => item.id}
      contentContainerStyle={thumb.list}
      renderItem={({ item }) => (
        <TouchableOpacity onPress={() => onTap(item)} activeOpacity={0.85}>
          <Image source={{ uri: item.uri }} style={thumb.img} />
        </TouchableOpacity>
      )}
    />
  );
}

const thumb = StyleSheet.create({
  list: { paddingHorizontal: 16, gap: 8 },
  img: {
    width: 56,
    height: 56,
    borderRadius: 10,
    borderWidth: 1.5,
    borderColor: "#2563EB",
  },
});

// Camera Screen
export default function CameraScreen() {
  const [permission, requestPermission] = useCameraPermissions();
  const [facing, setFacing] = useState<CameraType>("back");
  const [flash, setFlash] = useState<FlashMode>("off");
  const [zoom, setZoom] = useState(0);
  const [isReady, setIsReady] = useState(false);
  const [isTakingPhoto, setIsTakingPhoto] = useState(false);
  const [capturedPhotos, setCapturedPhotos] = useState<CapturedPhoto[]>([]);
  const [previewPhoto, setPreviewPhoto] = useState<CapturedPhoto | null>(null);
  const cameraRef = useRef<CameraView>(null);

  const flashIcons: Record<FlashMode, keyof typeof Ionicons.glyphMap> = {
    off: "flash-off",
    on: "flash",
    auto: "flash-outline",
  };

  const cycleFlash = () =>
    setFlash((prev) => (prev === "off" ? "on" : prev === "on" ? "auto" : "off"));

  const cycleZoom = () =>
    setZoom((prev) => (prev === 0 ? 0.5 : prev === 0.5 ? 1 : 0));

  const takePhoto = useCallback(async () => {
    if (!cameraRef.current || !isReady || isTakingPhoto) return;
    setIsTakingPhoto(true);
    try {
      const photo = await cameraRef.current.takePictureAsync({
        quality: 0.9,
        skipProcessing: false,
      });
      if (photo) {
        const newPhoto: CapturedPhoto = {
          id: Date.now().toString(),
          uri: photo.uri,
          timestamp: Date.now(),
        };
        setPreviewPhoto(newPhoto);
      }
    } catch (e) {
      console.error("Photo capture failed:", e);
    } finally {
      setIsTakingPhoto(false);
    }
  }, [isReady, isTakingPhoto]);

  const handleSave = async () => {
    if (!previewPhoto) return;
    try {
      const { status } = await MediaLibrary.requestPermissionsAsync();
      if (status !== "granted") {
        Alert.alert("Permission needed", "Allow media library access to save photos.");
        return;
      }
      await MediaLibrary.saveToLibraryAsync(previewPhoto.uri);
      setCapturedPhotos((prev) =>
        prev.some((p) => p.id === previewPhoto.id) ? prev : [previewPhoto, ...prev]
      );
      setPreviewPhoto(null);
      Alert.alert("Saved!", "Photo saved to your camera roll.");
    } catch {
      Alert.alert("Error", "Could not save photo.");
    }
  };

  const handleDiscard = () => {
    setPreviewPhoto(null);
  };

  // Permission gate
  if (!permission) return <View style={{ flex: 1, backgroundColor: "#0D1117" }} />;
  if (!permission.granted) return <PermissionScreen onRequest={requestPermission} />;

  const zoomLabel = zoom === 0 ? "1×" : zoom === 0.5 ? "2×" : "3×";

  return (
    <View style={styles.container}>
      <StatusBar hidden />

      <CameraView
        ref={cameraRef}
        style={styles.camera}
        facing={facing}
        flash={flash}
        zoom={zoom}
        onCameraReady={() => setIsReady(true)}
      >
        <View style={styles.overlay} pointerEvents="none">
          <View style={styles.bracketTL} />
          <View style={styles.bracketTR} />
          <View style={styles.bracketBL} />
          <View style={styles.bracketBR} />
        </View>
      </CameraView>

      <SafeAreaView style={styles.topBar}>
        <TouchableOpacity style={styles.controlBtn} onPress={cycleFlash}>
          <Ionicons name={flashIcons[flash]} size={22} color={flash === "on" ? "#FCD34D" : "#F0F4FF"} />
        </TouchableOpacity>

        <View style={styles.topCenter}>
          <Text style={styles.modeBadge}>PHOTO</Text>
        </View>

        <TouchableOpacity style={styles.controlBtn} onPress={cycleZoom}>
          <Text style={styles.zoomText}>{zoomLabel}</Text>
        </TouchableOpacity>
      </SafeAreaView>

      <View style={styles.bottomBar}>

        <View style={styles.stripRow}>
          <ThumbnailStrip
            photos={capturedPhotos}
            onTap={(photo) => setPreviewPhoto(photo)}
          />
        </View>

        <View style={styles.shutterRow}>
          <View style={styles.sideSlot}>
            {capturedPhotos.length > 0 ? (
              <TouchableOpacity onPress={() => setPreviewPhoto(capturedPhotos[0])}>
                <Image
                  source={{ uri: capturedPhotos[0].uri }}
                  style={styles.lastPhoto}
                />
                <View style={styles.lastPhotoCount}>
                  <Text style={styles.lastPhotoCountText}>{capturedPhotos.length}</Text>
                </View>
              </TouchableOpacity>
            ) : (
              <View style={styles.lastPhotoEmpty} />
            )}
          </View>

          <TouchableOpacity
            style={[styles.shutter, isTakingPhoto && styles.shutterPressed]}
            onPress={takePhoto}
            activeOpacity={0.9}
            disabled={!isReady || isTakingPhoto}
          >
            <View style={styles.shutterInner} />
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.sideSlot, styles.flipBtn]}
            onPress={() => setFacing((f) => (f === "back" ? "front" : "back"))}
            activeOpacity={0.8}
          >
            <Ionicons name="camera-reverse-outline" size={28} color="#F0F4FF" />
          </TouchableOpacity>
        </View>
      </View>

      {previewPhoto && (
        <PhotoPreview
          photo={previewPhoto}
          onDiscard={handleDiscard}
          onSave={handleSave}
        />
      )}
    </View>
  );
}

const SHUTTER_SIZE = 78;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#000",
  },
  camera: {
    flex: 1,
  },

  overlay: {
    ...StyleSheet.absoluteFillObject,
  },
  bracketTL: {
    position: "absolute",
    top: "20%",
    left: "8%",
    width: 32,
    height: 32,
    borderTopWidth: 2,
    borderLeftWidth: 2,
    borderColor: "rgba(255,255,255,0.5)",
    borderTopLeftRadius: 4,
  },
  bracketTR: {
    position: "absolute",
    top: "20%",
    right: "8%",
    width: 32,
    height: 32,
    borderTopWidth: 2,
    borderRightWidth: 2,
    borderColor: "rgba(255,255,255,0.5)",
    borderTopRightRadius: 4,
  },
  bracketBL: {
    position: "absolute",
    bottom: "20%",
    left: "8%",
    width: 32,
    height: 32,
    borderBottomWidth: 2,
    borderLeftWidth: 2,
    borderColor: "rgba(255,255,255,0.5)",
    borderBottomLeftRadius: 4,
  },
  bracketBR: {
    position: "absolute",
    bottom: "20%",
    right: "8%",
    width: 32,
    height: 32,
    borderBottomWidth: 2,
    borderRightWidth: 2,
    borderColor: "rgba(255,255,255,0.5)",
    borderBottomRightRadius: 4,
  },

  topBar: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingTop: Platform.OS === "ios" ? 0 : 10,
    paddingBottom: 12,
    backgroundColor: "rgba(0,0,0,0.35)",
  },
  controlBtn: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: "rgba(0,0,0,0.4)",
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.1)",
  },
  topCenter: {
    alignItems: "center",
  },
  modeBadge: {
    fontSize: 11,
    fontWeight: "800",
    color: "rgba(255,255,255,0.6)",
    letterSpacing: 3,
  },
  zoomText: {
    fontSize: 14,
    fontWeight: "700",
    color: "#FCD34D",
    letterSpacing: 0.5,
  },

  bottomBar: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: "rgba(0,0,0,0.6)",
    paddingBottom: Platform.OS === "ios" ? 36 : 16,
    paddingTop: 10,
  },
  stripRow: {
    height: 72,
    justifyContent: "center",
    marginBottom: 6,
  },
  shutterRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 32,
  },
  sideSlot: {
    width: 56,
    height: 56,
    alignItems: "center",
    justifyContent: "center",
  },
  lastPhoto: {
    width: 52,
    height: 52,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: "#fff",
  },
  lastPhotoEmpty: {
    width: 52,
    height: 52,
    borderRadius: 10,
    borderWidth: 1.5,
    borderColor: "rgba(255,255,255,0.2)",
    borderStyle: "dashed",
  },
  lastPhotoCount: {
    position: "absolute",
    bottom: -4,
    right: -4,
    backgroundColor: "#2563EB",
    borderRadius: 8,
    minWidth: 18,
    height: 18,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 4,
  },
  lastPhotoCountText: {
    color: "#fff",
    fontSize: 10,
    fontWeight: "700",
  },
  shutter: {
    width: SHUTTER_SIZE,
    height: SHUTTER_SIZE,
    borderRadius: SHUTTER_SIZE / 2,
    backgroundColor: "transparent",
    borderWidth: 3,
    borderColor: "#fff",
    alignItems: "center",
    justifyContent: "center",
  },
  shutterPressed: {
    borderColor: "#3B82F6",
    transform: [{ scale: 0.94 }],
  },
  shutterInner: {
    width: SHUTTER_SIZE - 16,
    height: SHUTTER_SIZE - 16,
    borderRadius: (SHUTTER_SIZE - 16) / 2,
    backgroundColor: "#fff",
  },
  flipBtn: {
    backgroundColor: "rgba(255,255,255,0.08)",
    borderRadius: 28,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.12)",
  },
});
