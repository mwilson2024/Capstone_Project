import { Ionicons } from "@expo/vector-icons";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  KeyboardTypeOptions,
  Modal,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { useEffect, useState } from "react";

export type FormField = {
  key: string;
  label: string;
  placeholder: string;
  secure?: boolean;
  keyboardType?: KeyboardTypeOptions;
  multiline?: boolean;
  autoCapitalize?: "none" | "sentences" | "words" | "characters";
};

type FormModalProps = {
  visible: boolean;
  title: string;
  subtitle?: string;
  fields: FormField[];
  submitLabel: string;
  submitting?: boolean;
  onClose: () => void;
  onSubmit: (values: Record<string, string>) => void;
};

export default function FormModal({
  visible,
  title,
  subtitle,
  fields,
  submitLabel,
  submitting = false,
  onClose,
  onSubmit,
}: FormModalProps) {
  const [values, setValues] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!visible) setValues({});
  }, [visible]);

  const handleSubmit = () => {
    const missing = fields.find((f) => !(values[f.key] ?? "").trim());
    if (missing) {
      Alert.alert("Missing Field", `Please fill in ${missing.label}.`);
      return;
    }

    const trimmed: Record<string, string> = {};
    fields.forEach((f) => {
      trimmed[f.key] = (values[f.key] ?? "").trim();
    });
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
        <View style={m.card}>
          <View style={m.header}>
            <View style={{ flex: 1 }}>
              <Text style={m.title}>{title}</Text>
              {subtitle && <Text style={m.subtitle}>{subtitle}</Text>}
            </View>
            <TouchableOpacity style={m.closeBtn} onPress={onClose}>
              <Ionicons name="close" size={22} color="#F0F4FF" />
            </TouchableOpacity>
          </View>

          <ScrollView
            style={m.scroll}
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
          >
            {fields.map((f) => (
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
                    placeholderTextColor="#8891A4"
                    value={values[f.key] ?? ""}
                    onChangeText={(t) =>
                      setValues((prev) => ({ ...prev, [f.key]: t }))
                    }
                    secureTextEntry={f.secure}
                    keyboardType={f.keyboardType}
                    autoCapitalize={
                      f.autoCapitalize ??
                      (f.secure || f.keyboardType === "email-address"
                        ? "none"
                        : "sentences")
                    }
                    autoCorrect={!f.secure}
                    multiline={f.multiline}
                  />
                </View>
              </View>
            ))}
          </ScrollView>

          <TouchableOpacity
            style={[m.submitBtn, submitting && m.submitBtnBusy]}
            onPress={handleSubmit}
            activeOpacity={0.85}
            disabled={submitting}
          >
            {submitting ? (
              <ActivityIndicator color="#fff" size="small" />
            ) : (
              <Text style={m.submitText}>{submitLabel}</Text>
            )}
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const m = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: "rgba(5,8,16,0.75)",
    justifyContent: "center",
    paddingHorizontal: 24,
  },
  card: {
    backgroundColor: "#161C27",
    borderRadius: 20,
    padding: 24,
    borderWidth: 1,
    borderColor: "#1E2A40",
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
    color: "#F0F4FF",
    letterSpacing: -0.6,
    fontFamily: Platform.OS === "ios" ? "Georgia" : "serif",
  },
  subtitle: {
    fontSize: 13,
    color: "#5A6A85",
    marginTop: 4,
  },
  closeBtn: {
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: "#0D1117",
    borderWidth: 1,
    borderColor: "#1E2A40",
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
    color: "#3B82F6",
    letterSpacing: 1.8,
    marginBottom: 8,
    fontFamily: Platform.OS === "ios" ? "Helvetica Neue" : "sans-serif",
  },
  inputWrapper: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#0D1117",
    borderRadius: 12,
    borderWidth: 1.5,
    borderColor: "#1E2A40",
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
    color: "#E8EDF8",
    fontFamily: Platform.OS === "ios" ? "Helvetica Neue" : "sans-serif",
  },
  inputMultiline: {
    height: 90,
    textAlignVertical: "top",
    paddingTop: 12,
  },
  submitBtn: {
    backgroundColor: "#2563EB",
    borderRadius: 12,
    height: 54,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    marginTop: 6,
    shadowColor: "#2563EB",
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
