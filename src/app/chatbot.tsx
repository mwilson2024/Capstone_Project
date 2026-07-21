import { Ionicons } from "@expo/vector-icons";
import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { apiFetch } from "@/lib/api";
import { ThemeColors } from "@/theme/colors";
import { useTheme } from "@/theme/ThemeContext";

type EventRecord = {
  event_id: number;
  user_id: number;
  name: string;
  event_date: string;
};
type EventsResponse = { events: EventRecord[] };
type PromptResponse = {
  inserted:
    | boolean
    | Array<{ prompt_request_id?: number }>;
  analysis: {
    response?: string;
    reason?: string;
    allowed?: boolean;
  };
};
type Message = {
  id: string;
  role: "assistant" | "user";
  text: string;
  canCreateVideo?: boolean;
  eventId?: number;
  requestId?: number | null;
  liked?: boolean;
  jobId?: number;
  jobStatus?: "queued" | "processing" | "completed" | "failed";
};

type CreateVideoResponse = {
  storyboard_id: number;
  status: string;
  job_id: number;
  job_status: string;
};

type VideoJobResponse = {
  job_id: number;
  event_id: number;
  job_type: string | null;
  status: string;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
};

const INTRO: Message = {
  id: "intro",
  role: "assistant",
  text: "Tell me how you want your event video to feel. I can help shape the theme, mood, and content direction.",
};

export default function ChatbotScreen() {
  const params = useLocalSearchParams<{ eventId?: string | string[] }>();
  const { colors: c } = useTheme();
  const styles = useMemo(() => makeStyles(c), [c]);
  const scrollRef = useRef<ScrollView>(null);
  const mountedRef = useRef(true);
  const [events, setEvents] = useState<EventRecord[]>([]);
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([INTRO]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [creatingForMessage, setCreatingForMessage] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      try {
        const eventResult = await apiFetch<EventsResponse>(
          "/users/me/events",
          undefined,
          "GET",
          controller.signal
        );
        setEvents(eventResult.events ?? []);
        const requestedEventId = Number(
          Array.isArray(params.eventId) ? params.eventId[0] : params.eventId
        );
        const initialEvent =
          eventResult.events?.find(
            (event) => event.event_id === requestedEventId
          ) ?? eventResult.events?.[0];
        setSelectedEventId(initialEvent?.event_id ?? null);
      } catch (caught) {
        if ((caught as Error).name !== "AbortError") {
          setLoadError(caught instanceof Error ? caught.message : "Assistant could not be loaded.");
        }
      } finally {
        setLoading(false);
      }
    })();
    return () => controller.abort();
  }, [params.eventId]);

  const selectedEvent = events.find((event) => event.event_id === selectedEventId);

  const updateJobMessage = (
    messageId: string,
    changes: Partial<Message>
  ) => {
    if (!mountedRef.current) return;
    setMessages((current) =>
      current.map((message) =>
        message.id === messageId ? { ...message, ...changes } : message
      )
    );
  };

  const monitorVideoJob = async (
    messageId: string,
    eventId: number,
    jobId: number
  ) => {
    let consecutiveErrors = 0;

    for (let attempt = 0; attempt < 200; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 3000));
      if (!mountedRef.current) return;

      try {
        const job = await apiFetch<VideoJobResponse>(
          `/events/${eventId}/jobs/${jobId}`
        );
        consecutiveErrors = 0;
        const status = job.status.toLowerCase();

        if (["completed", "complete", "success"].includes(status)) {
          updateJobMessage(messageId, {
            text: "Your generated video is ready. Open the event’s Generated tab to watch or download it.",
            jobStatus: "completed",
          });
          return;
        }

        if (["failed", "error"].includes(status)) {
          updateJobMessage(messageId, {
            text: job.error_message
              ? `Video creation failed: ${job.error_message}`
              : "Video creation failed. Please try again.",
            jobStatus: "failed",
          });
          return;
        }

        updateJobMessage(messageId, {
          text:
            status === "processing" || status === "running"
              ? "Your video is being created. This can take several minutes."
              : "Your video is queued and waiting to start.",
          jobStatus:
            status === "processing" || status === "running"
              ? "processing"
              : "queued",
        });
      } catch (caught) {
        consecutiveErrors += 1;
        if (consecutiveErrors >= 3) {
          updateJobMessage(messageId, {
            text:
              caught instanceof Error
                ? `Could not check video progress: ${caught.message}`
                : "Could not check video progress. Please refresh later.",
            jobStatus: "failed",
          });
          return;
        }
      }
    }

    updateJobMessage(messageId, {
      text: "Video processing is taking longer than expected. Check the event’s Generated tab later.",
      jobStatus: "processing",
    });
  };

  const send = async () => {
    const prompt = input.trim();
    if (!prompt || !selectedEvent || sending) return;
    const userMessage: Message = { id: `${Date.now()}-user`, role: "user", text: prompt };
    setMessages((current) => [...current, userMessage]);
    setInput("");
    setSending(true);
    requestAnimationFrame(() => scrollRef.current?.scrollToEnd({ animated: true }));
    try {
      const result = await apiFetch<PromptResponse>(
        "/prompt/analyze",
        {
          eventID: selectedEvent.event_id,
          userID: selectedEvent.user_id,
          guestID: null,
          prompt,
        },
        "POST"
      );
      const reply =
        result.analysis?.response ||
        result.analysis?.reason ||
        "I analyzed that request, but no response text was returned.";
      const insertedRow = Array.isArray(result.inserted)
        ? result.inserted[0]
        : null;
      setMessages((current) => [
        ...current,
        {
          id: `${Date.now()}-assistant`,
          role: "assistant",
          text: reply,
          canCreateVideo:
            result.analysis?.allowed === true &&
            Boolean(insertedRow?.prompt_request_id),
          eventId: selectedEvent.event_id,
          requestId: insertedRow?.prompt_request_id ?? null,
        },
      ]);
    } catch (caught) {
      const text = caught instanceof Error ? caught.message : "Please try again.";
      setMessages((current) => [
        ...current,
        { id: `${Date.now()}-error`, role: "assistant", text: `I couldn't analyze that request: ${text}` },
      ]);
    } finally {
      setSending(false);
      requestAnimationFrame(() => scrollRef.current?.scrollToEnd({ animated: true }));
    }
  };

  const createVideo = async (message: Message) => {
    if (!message.eventId || !message.requestId || creatingForMessage) return;
    setCreatingForMessage(message.id);
    try {
      const result = await apiFetch<CreateVideoResponse>(
        "/creation/storyboard",
        {
          event_id: message.eventId,
          request_id: message.requestId,
        },
        "POST"
      );
      if (!Number.isInteger(result.job_id) || result.job_id <= 0) {
        throw new Error(
          "The API did not return a processing job ID. Deploy the updated backend before creating videos."
        );
      }
      const progressMessageId = `${Date.now()}-creation`;
      setMessages((current) => [
        ...current.map((item) =>
          item.id === message.id ? { ...item, canCreateVideo: false } : item
        ),
        {
          id: progressMessageId,
          role: "assistant",
          text: "Your video is queued and waiting to start.",
          eventId: message.eventId,
          jobId: result.job_id,
          jobStatus: "queued",
        },
      ]);
      void monitorVideoJob(
        progressMessageId,
        message.eventId,
        result.job_id
      );
    } catch (caught) {
      Alert.alert(
        "Could not create video",
        caught instanceof Error ? caught.message : "Please try again."
      );
    } finally {
      setCreatingForMessage(null);
    }
  };

  const likePrompt = (messageId: string) => {
    setMessages((current) =>
      current.map((message) =>
        message.id === messageId ? { ...message, liked: true } : message
      )
    );
  };

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle={c.statusBar} />
      <KeyboardAvoidingView style={styles.safe} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <View style={styles.header}>
          <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={21} color={c.textBright} />
          </TouchableOpacity>
          <View style={{ flex: 1 }}>
            <Text style={styles.eyebrow}>VIDEO PLANNER</Text>
            <Text style={styles.title}>Assistant</Text>
          </View>
          <View style={styles.sparkle}>
            <Ionicons name="sparkles" size={19} color="#A78BFA" />
          </View>
        </View>

        {loading ? (
          <ActivityIndicator color={c.accent} style={{ marginTop: 50 }} />
        ) : loadError ? (
          <View style={styles.centerState}>
            <Ionicons name="alert-circle-outline" size={42} color={c.danger} />
            <Text style={styles.errorText}>{loadError}</Text>
          </View>
        ) : events.length === 0 ? (
          <View style={styles.centerState}>
            <Ionicons name="calendar-outline" size={45} color={c.textFaint} />
            <Text style={styles.centerTitle}>Create an event first</Text>
            <Text style={styles.centerCopy}>The assistant needs an event to save and analyze your video request.</Text>
          </View>
        ) : (
          <>
            <TouchableOpacity style={styles.eventSelector} onPress={() => setPickerOpen(true)}>
              <Ionicons name="calendar-outline" size={18} color={c.accent} />
              <View style={{ flex: 1 }}>
                <Text style={styles.selectorLabel}>CURRENT EVENT</Text>
                <Text style={styles.selectorValue}>{selectedEvent?.name}</Text>
              </View>
              <Ionicons name="chevron-down" size={18} color={c.textMuted} />
            </TouchableOpacity>

            <ScrollView
              ref={scrollRef}
              style={styles.messages}
              contentContainerStyle={styles.messageContent}
              keyboardShouldPersistTaps="handled"
              onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}
            >
              {messages.map((message) => (
                <View
                  key={message.id}
                  style={[
                    styles.bubble,
                    message.role === "user" ? styles.userBubble : styles.assistantBubble,
                  ]}
                >
                  {message.role === "assistant" ? (
                    <Ionicons name="sparkles" size={15} color="#A78BFA" style={{ marginBottom: 5 }} />
                  ) : null}
                  <Text style={[styles.bubbleText, message.role === "user" && styles.userBubbleText]}>
                    {message.text}
                  </Text>
                  {message.jobStatus ? (
                    <View style={styles.jobStatusRow}>
                      {message.jobStatus === "queued" ||
                      message.jobStatus === "processing" ? (
                        <ActivityIndicator size="small" color="#8B5CF6" />
                      ) : (
                        <Ionicons
                          name={
                            message.jobStatus === "completed"
                              ? "checkmark-circle"
                              : "alert-circle"
                          }
                          size={18}
                          color={
                            message.jobStatus === "completed"
                              ? "#10B981"
                              : c.danger
                          }
                        />
                      )}
                      <Text style={styles.jobStatusText}>
                        {message.jobStatus === "queued"
                          ? "QUEUED"
                          : message.jobStatus === "processing"
                            ? "PROCESSING"
                            : message.jobStatus === "completed"
                              ? "COMPLETED"
                              : "FAILED"}
                      </Text>
                    </View>
                  ) : null}
                  {message.canCreateVideo ? (
                    message.liked ? (
                      <TouchableOpacity
                        style={styles.createVideoButton}
                        disabled={creatingForMessage !== null}
                        onPress={() => void createVideo(message)}
                      >
                        {creatingForMessage === message.id ? (
                          <ActivityIndicator size="small" color="#fff" />
                        ) : (
                          <>
                            <Ionicons name="videocam" size={17} color="#fff" />
                            <Text style={styles.createVideoText}>CREATE VIDEO</Text>
                          </>
                        )}
                      </TouchableOpacity>
                    ) : (
                      <TouchableOpacity
                        style={styles.likeButton}
                        onPress={() => likePrompt(message.id)}
                      >
                        <Ionicons name="thumbs-up-outline" size={17} color="#8B5CF6" />
                        <Text style={styles.likeText}>LIKE THIS PROMPT</Text>
                      </TouchableOpacity>
                    )
                  ) : null}
                </View>
              ))}
              {sending ? (
                <View style={[styles.bubble, styles.assistantBubble, styles.typingBubble]}>
                  <ActivityIndicator size="small" color="#A78BFA" />
                  <Text style={styles.typingText}>Thinking…</Text>
                </View>
              ) : null}
            </ScrollView>

            <View style={styles.composer}>
              <TextInput
                style={styles.composerInput}
                value={input}
                onChangeText={setInput}
                placeholder="Describe your ideal event video…"
                placeholderTextColor={c.textMuted}
                multiline
                maxLength={1000}
                autoCorrect
                returnKeyType="send"
              />
              <TouchableOpacity
                style={[styles.sendButton, (!input.trim() || sending) && styles.sendDisabled]}
                disabled={!input.trim() || sending}
                onPress={() => void send()}
              >
                <Ionicons name="arrow-up" size={21} color="#fff" />
              </TouchableOpacity>
            </View>
          </>
        )}
      </KeyboardAvoidingView>

      <Modal visible={pickerOpen} transparent animationType="fade" onRequestClose={() => setPickerOpen(false)}>
        <View style={styles.modalBackdrop}>
          <Pressable style={StyleSheet.absoluteFill} onPress={() => setPickerOpen(false)} />
          <View style={styles.pickerCard}>
            <Text style={styles.pickerTitle}>Choose an event</Text>
            {events.map((event) => (
              <TouchableOpacity
                key={event.event_id}
                style={[styles.eventOption, event.event_id === selectedEventId && styles.eventOptionSelected]}
                onPress={() => {
                  setSelectedEventId(event.event_id);
                  setMessages([INTRO]);
                  setPickerOpen(false);
                }}
              >
                <Text style={styles.eventOptionText}>{event.name}</Text>
                {event.event_id === selectedEventId ? <Ionicons name="checkmark-circle" size={20} color={c.accent} /> : null}
              </TouchableOpacity>
            ))}
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const makeStyles = (c: ThemeColors) => {
  const isWeb = Platform.OS === "web";
  const isDark = c.statusBar === "light-content";
  const chatBackground = isWeb
    ? isDark
      ? "#0A0F1C"
      : "#E7ECF5"
    : c.bg;
  const assistantBackground = isWeb
    ? isDark
      ? "#1B2130"
      : "#F2ECFF"
    : c.surface;
  const assistantBorder = isWeb
    ? isDark
      ? "#37305C"
      : "#C9B8F5"
    : c.border;
  const composerBackground = isWeb
    ? isDark
      ? "#111827"
      : "#DDE4EF"
    : c.bg;
  const panelBorder = isWeb
    ? isDark
      ? "#293553"
      : "#CBD5E1"
    : c.border;
  const userBackground = isWeb ? "#6D28D9" : c.accentStrong;

  return StyleSheet.create({
    safe: { flex: 1, backgroundColor: chatBackground },
    header: { flexDirection: "row", alignItems: "center", gap: 13, paddingHorizontal: 18, paddingTop: 12, paddingBottom: 12 },
    backButton: { width: 42, height: 42, borderRadius: 13, backgroundColor: c.surface, borderWidth: 1, borderColor: panelBorder, alignItems: "center", justifyContent: "center" },
    eyebrow: { color: "#8B5CF6", fontSize: 9, fontWeight: "800", letterSpacing: 2 },
    title: { color: c.textBright, fontSize: 25, fontWeight: "800", letterSpacing: -0.6, fontFamily: Platform.OS === "ios" ? "Georgia" : "serif" },
    sparkle: { width: 42, height: 42, borderRadius: 13, backgroundColor: "#7C3AED22", alignItems: "center", justifyContent: "center" },
    eventSelector: { flexDirection: "row", alignItems: "center", gap: 11, marginHorizontal: 18, backgroundColor: c.surface, borderWidth: 1, borderColor: panelBorder, borderRadius: 14, padding: 13 },
    selectorLabel: { color: c.textMuted, fontSize: 8, letterSpacing: 1.5, fontWeight: "700" },
    selectorValue: { color: c.textPrimary, fontWeight: "600", marginTop: 2 },
    messages: { flex: 1 },
    messageContent: { padding: 18, gap: 12 },
    bubble: { maxWidth: "84%", paddingHorizontal: 15, paddingVertical: 12, borderRadius: 17 },
    assistantBubble: { alignSelf: "flex-start", backgroundColor: assistantBackground, borderWidth: 1, borderColor: assistantBorder, borderBottomLeftRadius: 5 },
    userBubble: { alignSelf: "flex-end", backgroundColor: userBackground, borderBottomRightRadius: 5 },
    bubbleText: { color: c.textPrimary, fontSize: 14, lineHeight: 20 },
    userBubbleText: { color: "#fff" },
    jobStatusRow: {
      flexDirection: "row",
      alignItems: "center",
      gap: 7,
      marginTop: 10,
    },
    jobStatusText: {
      color: c.textMuted,
      fontSize: 10,
      fontWeight: "800",
      letterSpacing: 1.1,
    },
    typingBubble: { flexDirection: "row", alignItems: "center", gap: 9 },
    typingText: { color: c.textMuted, fontSize: 13 },
    createVideoButton: { minHeight: 42, marginTop: 12, borderRadius: 11, backgroundColor: "#7C3AED", flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 7, paddingHorizontal: 13 },
    createVideoText: { color: "#fff", fontSize: 11, fontWeight: "800", letterSpacing: 1.2 },
    likeButton: { minHeight: 42, marginTop: 12, borderRadius: 11, borderWidth: 1, borderColor: "#8B5CF6", flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 7, paddingHorizontal: 13 },
    likeText: { color: "#8B5CF6", fontSize: 11, fontWeight: "800", letterSpacing: 1.1 },
    composer: { flexDirection: "row", alignItems: "flex-end", gap: 10, padding: 14, borderTopWidth: 1, borderTopColor: c.border, backgroundColor: composerBackground },
    composerInput: { flex: 1, maxHeight: 110, minHeight: 50, backgroundColor: c.surface, borderWidth: 1, borderColor: panelBorder, borderRadius: 16, paddingHorizontal: 15, paddingTop: 14, paddingBottom: 12, color: c.textPrimary, fontSize: 14 },
    sendButton: { width: 50, height: 50, borderRadius: 16, backgroundColor: "#7C3AED", alignItems: "center", justifyContent: "center" },
    sendDisabled: { opacity: 0.4 },
    centerState: { flex: 1, alignItems: "center", justifyContent: "center", paddingHorizontal: 34 },
    centerTitle: { color: c.textBright, fontSize: 19, fontWeight: "700", marginTop: 12 },
    centerCopy: { color: c.textMuted, textAlign: "center", lineHeight: 20, marginTop: 6 },
    errorText: { color: c.danger, textAlign: "center", marginTop: 10 },
    modalBackdrop: { flex: 1, justifyContent: "center", backgroundColor: "rgba(5,8,16,0.76)", padding: 24 },
    pickerCard: { backgroundColor: c.surface, borderWidth: 1, borderColor: c.border, borderRadius: 20, padding: 20 },
    pickerTitle: { color: c.textBright, fontSize: 21, fontWeight: "800", marginBottom: 14 },
    eventOption: { minHeight: 50, borderRadius: 12, paddingHorizontal: 13, flexDirection: "row", alignItems: "center", borderWidth: 1, borderColor: c.border, marginBottom: 9 },
    eventOptionSelected: { borderColor: c.accent, backgroundColor: c.bg },
    eventOptionText: { color: c.textPrimary, flex: 1, fontSize: 15 },
  });
};
