import { Ionicons } from "@expo/vector-icons";
import { router, usePathname } from "expo-router";
import { useMemo, useState } from "react";
import {
  Modal,
  Pressable,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { hasToken, setToken } from "@/lib/api";
import { ThemeColors } from "@/theme/colors";
import { useTheme } from "@/theme/ThemeContext";

const HIDDEN_ON = ["/", "/camera"];

export default function AccountButton() {
  const { colors: c } = useTheme();
  const insets = useSafeAreaInsets();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const s = useMemo(() => makeStyles(c), [c]);

  if (HIDDEN_ON.includes(pathname)) return null;

  const top = insets.top + 8;

  const signOut = () => {
    setToken("");
    setOpen(false);
    router.replace("/");
  };

  const goToLogin = () => {
    setOpen(false);
    router.push("/");
  };

  return (
    <>
      <TouchableOpacity
        style={[s.iconBtn, { top }]}
        onPress={() => setOpen(true)}
        activeOpacity={0.8}
        accessibilityLabel="Account"
      >
        <Ionicons name="person-circle-outline" size={24} color={c.accent} />
      </TouchableOpacity>

      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <Pressable style={s.backdrop} onPress={() => setOpen(false)}>
          <Pressable style={[s.popover, { top: top + 48 }]} onPress={() => {}}>
            {hasToken() ? (
              <>
                <Text style={s.statusText}>Signed in</Text>
                <TouchableOpacity style={s.row} onPress={signOut} activeOpacity={0.7}>
                  <Ionicons name="log-out-outline" size={18} color={c.danger} />
                  <Text style={s.signOutText}>Sign Out</Text>
                </TouchableOpacity>
              </>
            ) : (
              <>
                <Text style={s.statusText}>You are not signed in.</Text>
                <TouchableOpacity style={s.row} onPress={goToLogin} activeOpacity={0.7}>
                  <Text style={s.linkText}>Create Account</Text>
                </TouchableOpacity>
              </>
            )}
          </Pressable>
        </Pressable>
      </Modal>
    </>
  );
}

const makeStyles = (c: ThemeColors) =>
  StyleSheet.create({
    iconBtn: {
      position: "absolute",
      right: 16,
      zIndex: 50,
      width: 40,
      height: 40,
      borderRadius: 20,
      backgroundColor: c.surface,
      borderWidth: 1,
      borderColor: c.border,
      alignItems: "center",
      justifyContent: "center",
    },
    backdrop: {
      flex: 1,
      backgroundColor: "rgba(5,8,16,0.3)",
    },
    popover: {
      position: "absolute",
      right: 16,
      minWidth: 190,
      backgroundColor: c.surface,
      borderRadius: 14,
      borderWidth: 1,
      borderColor: c.border,
      padding: 14,
      shadowColor: "#000",
      shadowOffset: { width: 0, height: 8 },
      shadowOpacity: 0.3,
      shadowRadius: 20,
      elevation: 12,
    },
    statusText: {
      fontSize: 13,
      color: c.textMuted,
      marginBottom: 10,
    },
    row: {
      flexDirection: "row",
      alignItems: "center",
      gap: 8,
    },
    signOutText: {
      fontSize: 14,
      fontWeight: "600",
      color: c.danger,
    },
    linkText: {
      fontSize: 14,
      fontWeight: "600",
      color: c.accent,
      textDecorationLine: "underline",
    },
  });
