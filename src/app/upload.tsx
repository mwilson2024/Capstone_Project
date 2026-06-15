import { Ionicons } from "@expo/vector-icons";
import * as ImagePicker from "expo-image-picker";
import { useState } from "react";
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
  TouchableOpacity,
  View,
} from "react-native";

const { width: SCREEN_WIDTH } = Dimensions.get("window");
const THUMB = (SCREEN_WIDTH - 56) / 3;

type PickedPhoto = { id: string; uri: string };

export default function UploadScreen() {
  const [photos, setPhotos] = useState<PickedPhoto[]>([]);
  const [uploading, setUploading] = useState(false);
  const [done, setDone] = useState(false);

  //Pick from device library
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
      selectionLimit: 20,
    });
    if (!result.canceled) {
      const picked: PickedPhoto[] = result.assets.map((a, i) => ({
        id: `${Date.now()}-${i}`,
        uri: a.uri,
      }));
      setPhotos((prev) => [...prev, ...picked]);
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

  //Upload handler
  const handleUpload = async () => {
    setUploading(true);
    await new Promise((r) => setTimeout(r, 1800));
    setUploading(false);
    setDone(true);
    setPhotos([]);
  };

  return (
    <SafeAreaView style={s.safe}>
      <StatusBar barStyle="light-content" />

      <View style={s.header}>
        <View>
          <Text style={s.eyebrow}>DEVICE LIBRARY</Text>
          <Text style={s.title}>Upload</Text>
        </View>
        {photos.length > 0 && (
          <TouchableOpacity style={s.trashBtn} onPress={clearAll}>
            <Ionicons name="trash-outline" size={18} color="#F87171" />
          </TouchableOpacity>
        )}
      </View>

      <Text style={s.subtitle}>
        {photos.length > 0
          ? `${photos.length} photo${photos.length !== 1 ? "s" : ""} selected`
          : "No photos selected"}
      </Text>

      {photos.length === 0 ? (
        <View style={s.empty}>
          <TouchableOpacity
            style={s.dropZone}
            onPress={pickFromLibrary}
            activeOpacity={0.8}
          >
            <View style={s.iconRing}>
              <Ionicons name="images-outline" size={36} color="#3B82F6" />
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
              <Ionicons name="checkmark-circle" size={18} color="#10B981" />
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
                <Ionicons name="close-circle" size={22} color="#F87171" />
              </TouchableOpacity>
            </View>
          )}
          ListFooterComponent={
            <TouchableOpacity
              style={s.addMore}
              onPress={pickFromLibrary}
              activeOpacity={0.8}
            >
              <Ionicons name="add" size={20} color="#3B82F6" />
              <Text style={s.addMoreText}>Add More</Text>
            </TouchableOpacity>
          }
        />
      )}

      {photos.length > 0 && (
        <View style={s.footer}>
          <TouchableOpacity
            style={[s.uploadBtn, uploading && s.uploadBtnBusy]}
            onPress={handleUpload}
            activeOpacity={0.85}
            disabled={uploading}
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

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#0D1117" },

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
    color: "#3B82F6",
    letterSpacing: 2.5,
    marginBottom: 4,
  },
  title: {
    fontSize: 32,
    fontWeight: "800",
    color: "#F0F4FF",
    letterSpacing: -1,
    fontFamily: Platform.OS === "ios" ? "Georgia" : "serif",
  },
  trashBtn: {
    width: 40,
    height: 40,
    borderRadius: 12,
    backgroundColor: "#161C27",
    borderWidth: 1,
    borderColor: "#1E2A40",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 13,
    color: "#3B4A62",
    paddingHorizontal: 24,
    marginBottom: 20,
  },

  // Empty / drop zone
  empty: {
    flex: 1,
    paddingHorizontal: 20,
    justifyContent: "center",
    gap: 16,
  },
  dropZone: {
    backgroundColor: "#161C27",
    borderRadius: 20,
    borderWidth: 1.5,
    borderColor: "#1E2A40",
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
    backgroundColor: "#0D1117",
    borderWidth: 1.5,
    borderColor: "#1E2A40",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 4,
  },
  dropTitle: {
    fontSize: 20,
    fontWeight: "800",
    color: "#F0F4FF",
    letterSpacing: -0.5,
    fontFamily: Platform.OS === "ios" ? "Georgia" : "serif",
  },
  dropSub: {
    fontSize: 13,
    color: "#5A6A85",
    textAlign: "center",
    lineHeight: 20,
  },
  selectBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: "#2563EB",
    paddingHorizontal: 18,
    paddingVertical: 9,
    borderRadius: 20,
    marginTop: 8,
    shadowColor: "#2563EB",
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
    backgroundColor: "#0A2A1E",
    borderWidth: 1,
    borderColor: "#10B981",
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  successText: {
    fontSize: 14,
    color: "#10B981",
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
    backgroundColor: "#161C27",
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
    backgroundColor: "#161C27",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#1E2A40",
    paddingVertical: 14,
    marginTop: 8,
  },
  addMoreText: {
    fontSize: 14,
    fontWeight: "600",
    color: "#3B82F6",
  },

  footer: {
    paddingHorizontal: 20,
    paddingTop: 12,
    paddingBottom: Platform.OS === "ios" ? 8 : 16,
    borderTopWidth: 1,
    borderTopColor: "#1E2A40",
    backgroundColor: "#0D1117",
  },
  uploadBtn: {
    backgroundColor: "#2563EB",
    borderRadius: 14,
    height: 54,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    shadowColor: "#2563EB",
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.45,
    shadowRadius: 14,
    elevation: 8,
  },
  uploadBtnBusy: { opacity: 0.65 },
  uploadBtnText: {
    fontSize: 13,
    fontWeight: "800",
    color: "#fff",
    letterSpacing: 2,
  },
});
