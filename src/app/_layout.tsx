import { Ionicons } from "@expo/vector-icons";
import { Tabs } from "expo-router";
import { Platform, StyleSheet, View } from "react-native";

function TabIcon({
  name,
  color,
  focused,
  isCamera,
}: {
  name: keyof typeof Ionicons.glyphMap;
  color: string;
  focused: boolean;
  isCamera?: boolean;
}) {
  if (isCamera) {
    return (
      <View style={[styles.cameraIconWrapper, focused && styles.cameraIconFocused]}>
        <Ionicons name={name} size={22} color={focused ? "#fff" : "#93C5FD"} />
      </View>
    );
  }
  return (
    <View style={[styles.iconWrapper, focused && styles.iconFocused]}>
      <Ionicons name={name} size={22} color={color} />
    </View>
  );
}

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: styles.tabBar,
        tabBarItemStyle: {
      flex: 1,
      justifyContent: "center",
      alignItems: "center",
    },
        tabBarActiveTintColor: "#3B82F6",
        tabBarInactiveTintColor: "#3B4A62",
        tabBarLabelStyle: styles.tabLabel,
        tabBarShowLabel: true,
      }}
    >
      <Tabs.Screen
        name="gallery"
        options={{
          title: "Gallery",
          tabBarIcon: ({ color, focused }) => (
            <TabIcon
              name={focused ? "images" : "images-outline"}
              color={color}
              focused={focused}
            />
          ),
        }}
      />
      <Tabs.Screen
        name="camera"
        options={{
          title: "Camera",
          tabBarIcon: ({ focused }) => (
            <TabIcon
              name="camera"
              color="#fff"
              focused={focused}
              isCamera
            />
          ),
        }}
      />
      {/* ── NEW: Upload tab ── */}
      <Tabs.Screen
        name="upload"
        options={{
          title: "Upload",
          tabBarIcon: ({ color, focused }) => (
            <TabIcon
              name={focused ? "cloud-upload" : "cloud-upload-outline"}
              color={color}
              focused={focused}
            />
          ),
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
          title: "Settings",
          tabBarIcon: ({ color, focused }) => (
            <TabIcon
              name={focused ? "settings" : "settings-outline"}
              color={color}
              focused={focused}
            />
          ),
        }}
      />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    backgroundColor: "#161C27",
    borderTopWidth: 1,
    borderTopColor: "#1E2A40",
    height: Platform.OS === "ios" ? 82 : 64,
    paddingBottom: Platform.OS === "ios" ? 22 : 8,
    paddingTop: 8,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: -8 },
    shadowOpacity: 0.4,
    shadowRadius: 20,
    elevation: 20,
  },
  tabLabel: {
    fontSize: 11,
    fontWeight: "600",
    letterSpacing: 0.5,
    marginTop: 2,
  },
  iconWrapper: {
    width: 40,
    height: 32,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 10,
  },
  iconFocused: {
    backgroundColor: "rgba(59, 130, 246, 0.12)",
  },
  cameraIconWrapper: {
    width: 40,
    height: 32,
    borderRadius: 27,
    backgroundColor: "#1E2A40",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 0,
    borderWidth: 2,
    borderColor: "#2A3A55",
    shadowColor: "#3B82F6",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 6,
  },
  cameraIconFocused: {
    backgroundColor: "#2563EB",
    borderColor: "#3B82F6",
    shadowOpacity: 0.5,
  },
});
