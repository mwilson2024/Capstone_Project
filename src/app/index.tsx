import FormModal, { FormField } from "@/components/FormModal";
import { apiFetch, apiPublicFetch } from "@/lib/api";
import { useAuth } from "@/lib/AuthContext";
import { ThemeColors } from "@/theme/colors";
import { useTheme } from "@/theme/ThemeContext";
import { router } from "expo-router";
import { useMemo, useState } from "react";
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

const ACCOUNT_FIELDS: FormField[] = [
  { key: "user_name", label: "Username", placeholder: "Choose a username", autoCapitalize: "none" },
  { key: "first_name", label: "First Name", placeholder: "Your first name" },
  { key: "last_name", label: "Last Name", placeholder: "Your last name" },
  { key: "email", label: "Email", placeholder: "you@email.com", keyboardType: "email-address" },
  {
    key: "pwd",
    label: "Password",
    placeholder: "Create a password",
    secure: true,
    hint: "8–15 characters with uppercase, lowercase, a number, and $ @ # % or !.",
  },
];

const EVENT_FIELDS: FormField[] = [
  { key: "name", label: "Event Name", placeholder: "e.g. Sarah's Wedding" },
  { key: "type", label: "Type", placeholder: "Wedding, Birthday, Graduation…" },
  { key: "event_date", label: "Date", placeholder: "MM/DD/YYYY" },
  { key: "password", label: "Event Password", placeholder: "Password guests will use", secure: true },
  { key: "venue_name", label: "Venue", placeholder: "Venue name" },
  { key: "street", label: "Street", placeholder: "123 Main St" },
  { key: "city", label: "City", placeholder: "City" },
  { key: "state", label: "State", placeholder: "MI" },
  { key: "zip", label: "ZIP", placeholder: "48309", keyboardType: "number-pad" },
];

const parseDate = (s: string) => {
  const m = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(s.trim());
  if (!m) return null;
  const [mo, d, y] = [Number(m[1]), Number(m[2]), Number(m[3])];
  const date = new Date(y, mo - 1, d);
  if (date.getMonth() !== mo - 1 || date.getDate() !== d) return null;
  return `${y}-${String(mo).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
};

export default function WelcomeScreen() {
  const { colors: c } = useTheme();
  const { loggedIn, signIn } = useAuth();
  const styles = useMemo(() => makeStyles(c), [c]);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [modal, setModal] = useState<null | "account" | "event">(null);
  const [submitting, setSubmitting] = useState(false);
  const [loggingIn, setLoggingIn] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);
  const [modalError, setModalError] = useState<string | null>(null);

  const handleLogin = async () => {
    const login = username.trim();
    if (!login || !password) {
      setLoginError("Enter your username/email and password.");
      return;
    }

    setLoginError(null);
    setLoggingIn(true);
    try {
      const { access_token, user } = await apiPublicFetch("/users/login", {
        ...(login.includes("@") ? { email: login } : { user_name: login }),
        pwd: password,
      });
      await signIn(access_token, user);
      setPassword("");
      router.replace("/gallery");
    } catch (error: any) {
      setLoginError(
        `Unable to log in. ${error.message ?? "Check your login and try again."}`
      );
    } finally {
      setLoggingIn(false);
    }
  };

  const handleCreateAccount = async (values: Record<string, string>) => {
    const requiredFields: Array<[string, string]> = [
      ["user_name", "Username"],
      ["first_name", "First name"],
      ["last_name", "Last name"],
      ["email", "Email"],
      ["pwd", "Password"],
    ];
    const missing = requiredFields.find(([key]) => !values[key]?.trim());
    if (missing) {
      setModalError(`${missing[1]} is required.`);
      return;
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email)) {
      setModalError("Enter a valid email address containing @ and a domain.");
      return;
    }

    const passwordProblems = [
      values.pwd.length < 8 || values.pwd.length > 15
        ? "8–15 characters"
        : null,
      !/[A-Z]/.test(values.pwd) ? "one uppercase letter" : null,
      !/[a-z]/.test(values.pwd) ? "one lowercase letter" : null,
      !/\d/.test(values.pwd) ? "one number" : null,
      !/[$@#%!]/.test(values.pwd) ? "one of $ @ # % or !" : null,
    ].filter((item): item is string => Boolean(item));
    if (passwordProblems.length > 0) {
      setModalError(`Password requires ${passwordProblems.join(", ")}.`);
      return;
    }

    setModalError(null);
    setSubmitting(true);
    try {
      const user = await apiPublicFetch("/users/create", {
        ...values,
        phone: "",
        role: "user",
      });
      setModal(null);
      setModalError(null);
      Alert.alert("Account Created", `Welcome, ${user.first_name}!`);
    } catch (error: any) {
      setModalError(error.message ?? "Unable to create the account.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleCreateEventPress = () => {
    if (loggedIn) {
      setModal("event");
      return;
    }

    if (Platform.OS === "web") {
      setModalError(null);
      setModal("account");
      return;
    }

    Alert.alert(
      "Account Required",
      "Log in with the form above or create an account before creating an event.",
      [
        { text: "LOG IN", style: "cancel" },
        { text: "CREATE ACCOUNT", onPress: () => setModal("account") },
      ]
    );
  };

  const handleCreateEvent = async (values: Record<string, string>) => {
    if (!loggedIn) {
      setModal(null);
      Alert.alert(
        "Account Required",
        "Log in or create an account before creating an event."
      );
      return;
    }

    const eventDate = parseDate(values.event_date);
    if (!eventDate) {
      Alert.alert("Invalid Date", "Enter the date as MM/DD/YYYY.");
      return;
    }

    setSubmitting(true);
    try {
      await apiFetch("/events/create", {
        event: {
          user_id: 0,
          name: values.name,
          type: values.type,
          event_date: eventDate,
          password: values.password,
        },
        location: {
          venue_name: values.venue_name,
          street: values.street,
          city: values.city,
          state: values.state,
          zip: values.zip,
        },
      });
      setModal(null);
      Alert.alert("Event Created", `"${values.name}" is ready.`);
    } catch (error: any) {
      Alert.alert("Event Creation Failed", error.message ?? "Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle={c.statusBar} />

      {/* Background geometric shapes */}
      <View style={styles.bgCircleLarge} />
      <View style={styles.bgCircleSmall} />

      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        style={styles.inner}
      >
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.logoMark}>◆</Text>
          <Text style={styles.title}>Welcome!</Text>
          <Text style={styles.subtitle}>Sign in to continue</Text>
        </View>

        {/* Form Card */}
        <View style={styles.card}>
          {/* Username */}
          <View style={styles.fieldGroup}>
            <Text style={styles.label}>USERNAME</Text>
            <View style={styles.inputWrapper}>
              <Text style={styles.inputIcon}>⌂</Text>
              <TextInput
                style={styles.input}
                placeholder="Enter your username"
                placeholderTextColor={c.textMuted}
                value={username}
                onChangeText={(value) => {
                  setUsername(value);
                  setLoginError(null);
                }}
                autoCapitalize="none"
                autoCorrect={false}
              />
            </View>
          </View>

          {/* Password / Sign In */}
          <View style={styles.fieldGroup}>
            <Text style={styles.label}>PASSWORD</Text>
            <View style={styles.inputWrapper}>
              <Text style={styles.inputIcon}>⚿</Text>
              <TextInput
                style={styles.input}
                placeholder="Enter your password"
                placeholderTextColor={c.textMuted}
                value={password}
                onChangeText={(value) => {
                  setPassword(value);
                  setLoginError(null);
                }}
                secureTextEntry
              />
            </View>
          </View>

          {loginError ? (
            <View style={styles.loginErrorBox}>
              <Text style={styles.loginErrorIcon}>!</Text>
              <Text style={styles.loginErrorText}>{loginError}</Text>
            </View>
          ) : null}

          {/* Login Button */}
          <TouchableOpacity
            style={[styles.loginButton, loggingIn && { opacity: 0.65 }]}
            onPress={handleLogin}
            activeOpacity={0.85}
            disabled={loggingIn}
          >
            <Text style={styles.loginButtonText}>
              {loggingIn ? "LOGGING IN…" : "LOG IN"}
            </Text>
            {!loggingIn && <Text style={styles.loginArrow}>→</Text>}
          </TouchableOpacity>

          {/* Bottom Links Row */}
          <View style={styles.linksRow}>
            <TouchableOpacity
              style={styles.linkButton}
              activeOpacity={0.7}
              onPress={() => {
                setModalError(null);
                setModal("account");
              }}
            >
              <Text style={styles.linkText}>Create Account</Text>
              <View style={styles.linkUnderline} />
            </TouchableOpacity>

            <View style={styles.linkDivider} />

            <TouchableOpacity
              style={styles.linkButton}
              activeOpacity={0.7}
              onPress={handleCreateEventPress}
            >
              <Text style={styles.linkText}>Create Event</Text>
              <View style={styles.linkUnderline} />
            </TouchableOpacity>
          </View>
        </View>

        {/* Footer */}
        <Text style={styles.footerText}>
          By signing in you agree to our{" "}
          <Text style={styles.footerLink}>Terms & Privacy</Text>
        </Text>
      </KeyboardAvoidingView>

      <FormModal
        visible={modal === "account"}
        title="Create Account"
        subtitle="Sign up to get started"
        fields={ACCOUNT_FIELDS}
        submitLabel="SIGN UP"
        submitting={submitting}
        error={modal === "account" ? modalError : null}
        onChange={() => setModalError(null)}
        onClose={() => {
          setModalError(null);
          setModal(null);
        }}
        onSubmit={handleCreateAccount}
      />

      <FormModal
        visible={modal === "event"}
        title="Create Event"
        subtitle="Set up a new event gallery"
        fields={EVENT_FIELDS}
        submitLabel="CREATE EVENT"
        submitting={submitting}
        onClose={() => {
          setModalError(null);
          setModal(null);
        }}
        onSubmit={handleCreateEvent}
      />
    </View>
  );
}

const makeStyles = (c: ThemeColors) =>
  StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: c.bg,
      overflow: "hidden",
    },

    // Background decorative elements
    bgCircleLarge: {
      position: "absolute",
      width: 420,
      height: 420,
      borderRadius: 210,
      backgroundColor: c.decorLarge,
      top: -160,
      right: -120,
      opacity: 0.6,
    },
    bgCircleSmall: {
      position: "absolute",
      width: 200,
      height: 200,
      borderRadius: 100,
      backgroundColor: c.decorSmall,
      bottom: 80,
      left: -80,
      opacity: 0.25,
    },

    inner: {
      flex: 1,
      width: "100%",
      maxWidth: 620,
      alignSelf: "center",
      justifyContent: "center",
      paddingHorizontal: 28,
      paddingTop: 20,
    },

    // Header
    header: {
      marginBottom: 36,
      paddingLeft: 4,
    },
    logoMark: {
      fontSize: 22,
      color: c.accentStrong,
      marginBottom: 16,
    },
    title: {
      fontSize: 38,
      fontWeight: "800",
      color: c.textBright,
      letterSpacing: -1.2,
      lineHeight: 44,
      fontFamily: Platform.OS === "ios" ? "Georgia" : "serif",
    },
    subtitle: {
      fontSize: 15,
      color: c.textMuted,
      marginTop: 6,
      letterSpacing: 0.3,
      fontFamily: Platform.OS === "ios" ? "Helvetica Neue" : "sans-serif",
    },

    // Card
    card: {
      backgroundColor: c.surface,
      borderRadius: 20,
      padding: 28,
      borderWidth: 1,
      borderColor: c.border,
      shadowColor: "#000",
      shadowOffset: { width: 0, height: 12 },
      shadowOpacity: 0.5,
      shadowRadius: 30,
      elevation: 16,
    },

    // Fields
    fieldGroup: {
      marginBottom: 20,
    },
    label: {
      fontSize: 11,
      fontWeight: "700",
      color: c.accent,
      letterSpacing: 1.8,
      marginBottom: 8,
      fontFamily: Platform.OS === "ios" ? "Helvetica Neue" : "sans-serif",
    },
    inputWrapper: {
      flexDirection: "row",
      alignItems: "center",
      backgroundColor: c.bg,
      borderRadius: 12,
      borderWidth: 1.5,
      borderColor: c.border,
      paddingHorizontal: 14,
    },
    inputIcon: {
      fontSize: 16,
      color: c.textFaint,
      marginRight: 10,
    },
    input: {
      flex: 1,
      height: 50,
      fontSize: 15,
      color: c.textPrimary,
      fontFamily: Platform.OS === "ios" ? "Helvetica Neue" : "sans-serif",
    },
    loginErrorBox: {
      flexDirection: "row",
      alignItems: "center",
      gap: 9,
      paddingHorizontal: 12,
      paddingVertical: 10,
      marginTop: -5,
      marginBottom: 12,
      borderWidth: 1,
      borderColor: c.danger,
      borderRadius: 10,
      backgroundColor: c.bg,
    },
    loginErrorIcon: {
      width: 20,
      height: 20,
      textAlign: "center",
      color: "#fff",
      fontSize: 13,
      fontWeight: "800",
      borderRadius: 10,
      backgroundColor: c.danger,
    },
    loginErrorText: { flex: 1, color: c.danger, fontSize: 13, lineHeight: 18 },

    // Login Button
    loginButton: {
      backgroundColor: c.accentStrong,
      borderRadius: 12,
      height: 54,
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "center",
      marginTop: 8,
      marginBottom: 28,
      shadowColor: c.accentStrong,
      shadowOffset: { width: 0, height: 6 },
      shadowOpacity: 0.45,
      shadowRadius: 14,
      elevation: 8,
      gap: 10,
    },
    loginButtonText: {
      fontSize: 14,
      fontWeight: "800",
      color: "#FFFFFF",
      letterSpacing: 2.5,
      fontFamily: Platform.OS === "ios" ? "Helvetica Neue" : "sans-serif",
    },
    loginArrow: {
      fontSize: 18,
      color: "#93C5FD",
    },

    // Bottom Links
    linksRow: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "center",
      gap: 0,
    },
    linkButton: {
      alignItems: "center",
      paddingHorizontal: 16,
    },
    linkText: {
      fontSize: 13.5,
      color: c.accent,
      fontWeight: "600",
      letterSpacing: 0.2,
      fontFamily: Platform.OS === "ios" ? "Helvetica Neue" : "sans-serif",
    },
    linkUnderline: {
      height: 1,
      backgroundColor: c.accentStrong,
      marginTop: 3,
      width: "100%",
      opacity: 0.5,
    },
    linkDivider: {
      width: 1,
      height: 20,
      backgroundColor: c.border,
    },

    // Footer
    footerText: {
      textAlign: "center",
      color: c.textFaint,
      fontSize: 12,
      marginTop: 32,
      letterSpacing: 0.2,
      fontFamily: Platform.OS === "ios" ? "Helvetica Neue" : "sans-serif",
    },
    footerLink: {
      color: c.accent,
      fontWeight: "600",
    },
  });
