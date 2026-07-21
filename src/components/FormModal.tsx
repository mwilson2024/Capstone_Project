import { Ionicons } from "@expo/vector-icons";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  KeyboardTypeOptions,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { useEffect, useMemo, useState } from "react";
import { ThemeColors } from "@/theme/colors";
import { useTheme } from "@/theme/ThemeContext";

const EMPTY_INITIAL_VALUES: Record<string, string> = {};

export type FormField = {
  key: string;
  label: string;
  placeholder: string;
  required?: boolean;
  secure?: boolean;
  keyboardType?: KeyboardTypeOptions;
  multiline?: boolean;
  autoCapitalize?: "none" | "sentences" | "words" | "characters";
  hint?: string;
};

type FormModalProps = {
  visible: boolean;
  title: string;
  subtitle?: string;
  fields: FormField[];
  submitLabel: string;
  submitting?: boolean;
  error?: string | null;
  initialValues?: Record<string, string>;
  onClose: () => void;
  onSubmit: (values: Record<string, string>) => void;
  onChange?: () => void;
};

export default function FormModal({
  visible,
  title,
  subtitle,
  fields,
  submitLabel,
  submitting = false,
  error = null,
  initialValues = EMPTY_INITIAL_VALUES,
  onClose,
  onSubmit,
  onChange,
}: FormModalProps) {
  const { colors: c } = useTheme();
  const m = useMemo(() => makeStyles(c), [c]);
  const [values, setValues] = useState<Record<string, string>>({});
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    setValues(visible ? initialValues : {});
    setValidationError(null);
  }, [visible, initialValues]);

  const handleSubmit = () => {
    const missing = fields.find(
      (f) => f.required !== false && !(values[f.key] ?? "").trim()
    );
    if (missing) {
      setValidationError(`Please fill in ${missing.label}.`);
      return;
    }

    const trimmed: Record<string, string> = {};
    fields.forEach((f) => {
      trimmed[f.key] = (values[f.key] ?? "").trim();
    });
    setValidationError(null);
    onSubmit(trimmed);
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      statusBarTranslucent
      onRequestClose={onClose}
    >
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        style={m.backdrop}
      >
        <Pressable style={StyleSheet.absoluteFill} onPress={onClose} />
        <View style={m.card}>
          <View style={m.header}>
            <View style={{ flex: 1 }}>
              <Text style={m.title}>{title}</Text>
              {subtitle && <Text style={m.subtitle}>{subtitle}</Text>}
            </View>
            <TouchableOpacity style={m.closeBtn} onPress={onClose}>
              <Ionicons name="close" size={22} color={c.textBright} />
            </TouchableOpacity>
          </View>

          {error || validationError ? (
            <View style={m.errorBox}>
              <Ionicons name="alert-circle-outline" size={18} color={c.danger} />
              <Text style={m.errorText}>{error || validationError}</Text>
            </View>
          ) : null}

          <ScrollView
            style={m.scroll}
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
          >
            {fields.map((f, index) => (
              <View key={f.key} style={m.fieldGroup}>
                <Text style={m.label}>{f.label.toUpperCase()}</Text>
                <View
                  style={[
                    m.inputWrapper,
                    f.multiline && m.inputWrapperMultiline,
                  ]}
                >
                  <TextInput
                    style={[m.input, f.multiline && m.inputMultiline]}
                    placeholder={f.placeholder}
                    placeholderTextColor={c.textMuted}
                    value={values[f.key] ?? ""}
                    onChangeText={(t) => {
                      setValidationError(null);
                      onChange?.();
                      setValues((prev) => ({ ...prev, [f.key]: t }));
                    }}
                    secureTextEntry={f.secure}
                    keyboardType={f.keyboardType}
                    autoCapitalize={
                      f.autoCapitalize ??
                      (f.secure || f.keyboardType === "email-address"
                        ? "none"
                        : "sentences")
                    }
                    autoCorrect={!f.secure && f.keyboardType !== "email-address"}
                    multiline={f.multiline}
                    returnKeyType={index === fields.length - 1 ? "done" : "next"}
                    onSubmitEditing={
                      index === fields.length - 1 ? handleSubmit : undefined
                    }
                  />
                </View>
                {f.hint ? <Text style={m.hint}>{f.hint}</Text> : null}
              </View>
            ))}
          </ScrollView>

          {Platform.OS === "web" ? (
            <button
              type="button"
              onClick={handleSubmit}
              disabled={submitting}
              aria-label={submitLabel}
              style={{
                backgroundColor: c.accentStrong,
                border: "none",
                borderRadius: 12,
                height: 54,
                width: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                marginTop: 6,
                cursor: submitting ? "default" : "pointer",
                opacity: submitting ? 0.65 : 1,
              }}
            >
              {submitting ? (
                <ActivityIndicator color="#fff" size="small" />
              ) : (
                <Text style={m.submitText}>{submitLabel}</Text>
              )}
            </button>
          ) : (
            <Pressable
              style={[m.submitBtn, submitting && m.submitBtnBusy]}
              onPress={handleSubmit}
              disabled={submitting}
              accessibilityRole="button"
              accessibilityLabel={submitLabel}
            >
              {submitting ? (
                <ActivityIndicator color="#fff" size="small" />
              ) : (
                <Text style={m.submitText}>{submitLabel}</Text>
              )}
            </Pressable>
          )}
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const makeStyles = (c: ThemeColors) =>
  StyleSheet.create({
    backdrop: {
      flex: 1,
      backgroundColor: "rgba(5,8,16,0.75)",
      justifyContent: "center",
      paddingHorizontal: 24,
    },
    card: {
      backgroundColor: c.surface,
      borderRadius: 20,
      padding: 24,
      borderWidth: 1,
      borderColor: c.border,
      width: "100%",
      maxWidth: 560,
      alignSelf: "center",
      maxHeight: "85%",
      shadowColor: "#000",
      shadowOffset: { width: 0, height: 12 },
      shadowOpacity: 0.5,
      shadowRadius: 30,
      elevation: 16,
    },
    header: {
      flexDirection: "row",
      alignItems: "flex-start",
      marginBottom: 18,
    },
    title: {
      fontSize: 24,
      fontWeight: "800",
      color: c.textBright,
      letterSpacing: -0.6,
      fontFamily: Platform.OS === "ios" ? "Georgia" : "serif",
    },
    subtitle: {
      fontSize: 13,
      color: c.textMuted,
      marginTop: 4,
    },
    errorBox: {
      flexDirection: "row",
      alignItems: "center",
      gap: 8,
      paddingHorizontal: 12,
      paddingVertical: 10,
      marginBottom: 14,
      borderRadius: 10,
      borderWidth: 1,
      borderColor: c.danger,
      backgroundColor: c.bg,
    },
    errorText: { flex: 1, color: c.danger, fontSize: 13, lineHeight: 18 },
    closeBtn: {
      width: 36,
      height: 36,
      borderRadius: 10,
      backgroundColor: c.bg,
      borderWidth: 1,
      borderColor: c.border,
      alignItems: "center",
      justifyContent: "center",
    },
    scroll: {
      flexGrow: 0,
    },
    fieldGroup: {
      marginBottom: 16,
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
    inputWrapperMultiline: {
      alignItems: "flex-start",
      paddingVertical: 4,
    },
    input: {
      flex: 1,
      height: 50,
      fontSize: 15,
      color: c.textPrimary,
      fontFamily: Platform.OS === "ios" ? "Helvetica Neue" : "sans-serif",
    },
    inputMultiline: {
      height: 90,
      textAlignVertical: "top",
      paddingTop: 12,
    },
    hint: { color: c.textMuted, fontSize: 11, lineHeight: 16, marginTop: 5 },
    submitBtn: {
      backgroundColor: c.accentStrong,
      borderRadius: 12,
      height: 54,
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "center",
      gap: 10,
      marginTop: 6,
      shadowColor: c.accentStrong,
      shadowOffset: { width: 0, height: 6 },
      shadowOpacity: 0.45,
      shadowRadius: 14,
      elevation: 8,
    },
    submitBtnBusy: { opacity: 0.65 },
    submitText: {
      fontSize: 14,
      fontWeight: "800",
      color: "#FFFFFF",
      letterSpacing: 2.5,
      fontFamily: Platform.OS === "ios" ? "Helvetica Neue" : "sans-serif",
    },
  });
