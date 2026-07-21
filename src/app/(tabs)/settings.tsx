import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import * as WebBrowser from "expo-web-browser";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Platform,
  RefreshControl,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Switch,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import FormModal, { FormField } from "@/components/FormModal";
import { apiFetch } from "@/lib/api";
import { AuthUser, useAuth } from "@/lib/AuthContext";
import { ThemeColors } from "@/theme/colors";
import { useTheme } from "@/theme/ThemeContext";

const VERSION = "1.0.0";

const PROFILE_FIELDS: FormField[] = [
  { key: "first_name", label: "First name", placeholder: "First name", autoCapitalize: "words" },
  { key: "last_name", label: "Last name", placeholder: "Last name", autoCapitalize: "words" },
  { key: "user_name", label: "Username", placeholder: "Username", autoCapitalize: "none" },
  { key: "email", label: "Email", placeholder: "you@example.com", keyboardType: "email-address" },
  { key: "phone", label: "Phone number", placeholder: "(555) 555-5555", keyboardType: "phone-pad" },
];

const PASSWORD_FIELDS: FormField[] = [
  { key: "current_password", label: "Current password", placeholder: "Current password", secure: true },
  { key: "new_password", label: "New password", placeholder: "New password", secure: true },
];

function DetailRow({
  icon,
  label,
  value,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  value: string;
}) {
  const { colors: c } = useTheme();
  const styles = useMemo(() => makeStyles(c), [c]);
  return (
    <View style={styles.detailRow}>
      <View style={styles.iconBox}>
        <Ionicons name={icon} size={18} color={c.accent} />
      </View>
      <View style={styles.detailText}>
        <Text style={styles.detailLabel}>{label}</Text>
        <Text style={styles.detailValue}>{value || "Not provided"}</Text>
      </View>
    </View>
  );
}

export default function SettingsScreen() {
  const { colors: c, isDark, setDark } = useTheme();
  const {
    signOut,
    user: cachedUser,
    setUserProfile,
  } = useAuth();
  const styles = useMemo(() => makeStyles(c), [c]);
  const [profile, setProfile] = useState<AuthUser | null>(cachedUser);
  const [loading, setLoading] = useState(!cachedUser);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const [passwordOpen, setPasswordOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  const loadProfile = useCallback(async () => {
    try {
      setError(null);
      const current = await apiFetch<AuthUser>("/users/me");
      setProfile(current);
      await setUserProfile(current);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Profile could not be loaded.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [setUserProfile]);

  useEffect(() => {
    if (cachedUser) {
      setProfile(cachedUser);
      setLoading(false);
      setError(null);
    } else {
      void loadProfile();
    }
  }, [cachedUser, loadProfile]);

  const initialProfileValues = useMemo<Record<string, string>>(
    () =>
      profile
        ? {
            first_name: profile.first_name,
            last_name: profile.last_name,
            user_name: profile.user_name,
            email: profile.email,
            phone: profile.phone,
          }
        : ({} as Record<string, string>),
    [profile]
  );

  const saveProfile = async (values: Record<string, string>) => {
    setSaving(true);
    try {
      const updated = await apiFetch<AuthUser>("/users/me", values, "PATCH");
      setProfile(updated);
      await setUserProfile(updated);
      setProfileOpen(false);
      Alert.alert("Profile updated", "Your account details have been saved.");
    } catch (caught) {
      Alert.alert("Could not update profile", caught instanceof Error ? caught.message : "Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const savePassword = async (values: Record<string, string>) => {
    setSaving(true);
    try {
      await apiFetch("/users/me/password", values, "PATCH");
      setPasswordOpen(false);
      Alert.alert("Password updated", "Use your new password the next time you sign in.");
    } catch (caught) {
      Alert.alert("Could not update password", caught instanceof Error ? caught.message : "Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const finishLogOut = async () => {
    await signOut();
    router.replace("/");
  };

  const logOut = () => {
    if (Platform.OS === "web") {
      const confirmed = (globalThis as any).confirm?.(
        "Are you sure you want to log out?"
      );
      if (confirmed) void finishLogOut();
      return;
    }

    Alert.alert("Log out", "Are you sure you want to log out?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Log out",
        style: "destructive",
        onPress: () => void finishLogOut(),
      },
    ]);
  };

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle={c.statusBar} />
      <View style={styles.header}>
        <Text style={styles.eyebrow}>YOUR ACCOUNT</Text>
        <Text style={styles.title}>Settings</Text>
      </View>

      {loading ? (
        <ActivityIndicator color={c.accent} style={styles.loader} />
      ) : (
        <ScrollView
          contentContainerStyle={styles.content}
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              tintColor={c.accent}
              onRefresh={() => {
                setRefreshing(true);
                void loadProfile();
              }}
            />
          }
        >
          {error ? (
            <TouchableOpacity style={styles.errorCard} onPress={() => void loadProfile()}>
              <Ionicons name="alert-circle-outline" size={22} color={c.danger} />
              <View style={{ flex: 1 }}>
                <Text style={styles.errorTitle}>Profile unavailable</Text>
                <Text style={styles.errorText}>{error} Tap to retry.</Text>
              </View>
            </TouchableOpacity>
          ) : profile ? (
            <>
              <View style={styles.profileCard}>
                <View style={styles.avatar}>
                  <Text style={styles.avatarText}>
                    {(profile.first_name[0] ?? "") + (profile.last_name[0] ?? "")}
                  </Text>
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.name}>{profile.first_name} {profile.last_name}</Text>
                  <Text style={styles.username}>@{profile.user_name} · {profile.role}</Text>
                </View>
                <TouchableOpacity style={styles.editButton} onPress={() => setProfileOpen(true)}>
                  <Ionicons name="pencil" size={17} color="#fff" />
                </TouchableOpacity>
              </View>

              <Text style={styles.sectionTitle}>PROFILE</Text>
              <View style={styles.card}>
                <DetailRow icon="mail-outline" label="Email" value={profile.email} />
                <View style={styles.divider} />
                <DetailRow icon="call-outline" label="Phone number" value={profile.phone} />
              </View>

              <Text style={styles.sectionTitle}>SECURITY</Text>
              <TouchableOpacity style={styles.actionRow} onPress={() => setPasswordOpen(true)}>
                <View style={styles.iconBox}>
                  <Ionicons name="lock-closed-outline" size={18} color="#10B981" />
                </View>
                <Text style={styles.actionText}>Change password</Text>
                <Ionicons name="chevron-forward" size={17} color={c.textFaint} />
              </TouchableOpacity>
            </>
          ) : null}

          <Text style={styles.sectionTitle}>APPEARANCE</Text>
          <View style={styles.actionRow}>
            <View style={styles.iconBox}>
              <Ionicons name="moon-outline" size={18} color="#A855F7" />
            </View>
            <Text style={styles.actionText}>Dark mode</Text>
            <Switch
              value={isDark}
              onValueChange={setDark}
              trackColor={{ false: c.border, true: c.switchTrackOn }}
              thumbColor={isDark ? c.accent : c.switchThumbOff}
            />
          </View>

          <Text style={styles.sectionTitle}>SUPPORT</Text>
          <View style={styles.card}>
            <TouchableOpacity
              style={styles.actionRowInner}
              onPress={() => void WebBrowser.openBrowserAsync("https://github.com/GageMG/Capstone_Project#readme")}
            >
              <Ionicons name="help-circle-outline" size={19} color={c.accent} />
              <Text style={styles.actionText}>Help center</Text>
              <Ionicons name="open-outline" size={16} color={c.textFaint} />
            </TouchableOpacity>
            <View style={styles.divider} />
            <View style={styles.actionRowInner}>
              <Ionicons name="information-circle-outline" size={19} color={c.textMuted} />
              <Text style={styles.actionText}>App version</Text>
              <Text style={styles.value}>{VERSION}</Text>
            </View>
          </View>

          <TouchableOpacity style={styles.logoutButton} onPress={logOut}>
            <Ionicons name="log-out-outline" size={19} color={c.danger} />
            <Text style={styles.logoutText}>Log out</Text>
          </TouchableOpacity>
        </ScrollView>
      )}

      <FormModal
        visible={profileOpen}
        title="Edit profile"
        subtitle="These values are saved to your account."
        fields={PROFILE_FIELDS}
        initialValues={initialProfileValues}
        submitLabel="SAVE PROFILE"
        submitting={saving}
        onClose={() => setProfileOpen(false)}
        onSubmit={saveProfile}
      />
      <FormModal
        visible={passwordOpen}
        title="Change password"
        fields={PASSWORD_FIELDS}
        submitLabel="UPDATE PASSWORD"
        submitting={saving}
        onClose={() => setPasswordOpen(false)}
        onSubmit={savePassword}
      />
    </SafeAreaView>
  );
}

const makeStyles = (c: ThemeColors) =>
  StyleSheet.create({
    safe: { flex: 1, backgroundColor: c.bg },
    header: { paddingHorizontal: 24, paddingTop: 20, paddingBottom: 16 },
    eyebrow: { fontSize: 10, fontWeight: "700", color: c.accent, letterSpacing: 2.5, marginBottom: 4 },
    title: { fontSize: 32, fontWeight: "800", color: c.textBright, letterSpacing: -1, fontFamily: Platform.OS === "ios" ? "Georgia" : "serif" },
    loader: { marginTop: 48 },
    content: { paddingHorizontal: 20, paddingBottom: 40 },
    profileCard: { flexDirection: "row", alignItems: "center", gap: 14, backgroundColor: c.surface, borderWidth: 1, borderColor: c.border, borderRadius: 18, padding: 18, marginBottom: 26 },
    avatar: { width: 54, height: 54, borderRadius: 18, backgroundColor: c.accentStrong, alignItems: "center", justifyContent: "center" },
    avatarText: { color: "#fff", fontSize: 18, fontWeight: "800" },
    name: { color: c.textBright, fontSize: 19, fontWeight: "700" },
    username: { color: c.textMuted, fontSize: 12, marginTop: 4, textTransform: "capitalize" },
    editButton: { width: 38, height: 38, borderRadius: 12, backgroundColor: c.accentStrong, alignItems: "center", justifyContent: "center" },
    sectionTitle: { color: c.accent, fontSize: 11, fontWeight: "700", letterSpacing: 2, marginLeft: 4, marginBottom: 9, marginTop: 2 },
    card: { backgroundColor: c.surface, borderWidth: 1, borderColor: c.border, borderRadius: 16, overflow: "hidden", marginBottom: 26 },
    detailRow: { flexDirection: "row", alignItems: "center", gap: 12, padding: 15 },
    detailText: { flex: 1 },
    detailLabel: { color: c.textMuted, fontSize: 11, textTransform: "uppercase", letterSpacing: 1 },
    detailValue: { color: c.textPrimary, fontSize: 15, marginTop: 3 },
    iconBox: { width: 34, height: 34, borderRadius: 10, backgroundColor: c.bg, alignItems: "center", justifyContent: "center" },
    divider: { height: 1, backgroundColor: c.divider, marginLeft: 62 },
    actionRow: { flexDirection: "row", alignItems: "center", gap: 12, backgroundColor: c.surface, borderWidth: 1, borderColor: c.border, borderRadius: 16, padding: 15, marginBottom: 26 },
    actionRowInner: { flexDirection: "row", alignItems: "center", gap: 12, padding: 15 },
    actionText: { flex: 1, color: c.textPrimary, fontSize: 15, fontWeight: "500" },
    value: { color: c.textMuted, fontSize: 14 },
    errorCard: { flexDirection: "row", gap: 12, backgroundColor: c.surface, borderColor: c.danger, borderWidth: 1, borderRadius: 16, padding: 16, marginBottom: 24 },
    errorTitle: { color: c.danger, fontWeight: "700" },
    errorText: { color: c.textMuted, marginTop: 3, lineHeight: 18 },
    logoutButton: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 9, padding: 15, borderWidth: 1, borderColor: c.danger, borderRadius: 14 },
    logoutText: { color: c.danger, fontWeight: "700", fontSize: 15 },
  });
