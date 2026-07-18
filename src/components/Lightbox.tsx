import { Ionicons } from "@expo/vector-icons";
import { useState } from "react";
import {
  Dimensions,
  FlatList,
  Image,
  Modal,
  Platform,
  StatusBar,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

const { width: SCREEN_WIDTH } = Dimensions.get("window");

export type LightboxPhoto = { id: string; uri: string };

export default function Lightbox({
  photos,
  startIndex,
  onClose,
}: {
  photos: LightboxPhoto[];
  startIndex: number;
  onClose: () => void;
}) {
  const [current, setCurrent] = useState(startIndex);

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
            setCurrent(Math.round(e.nativeEvent.contentOffset.x / SCREEN_WIDTH));
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
