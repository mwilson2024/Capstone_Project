import { CameraView, useCameraPermissions } from 'expo-camera';
import { useRef, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

export default function UploadScreen() {
  const [permission, requestPermission] = useCameraPermissions();
  const [cameraOpen, setCameraOpen] = useState(false);
  const cameraRef = useRef<CameraView>(null);

  if (!permission) {
    return <View style={styles.page} />;
  }

  if (!permission.granted) {
    return (
      <View style={styles.page}>
        <Text style={styles.title}>Camera Permission Needed</Text>
        <Text style={styles.subtitle}>
          EventLens needs camera access so guests can take photos during an event.
        </Text>

        <Pressable style={styles.primaryButton} onPress={requestPermission}>
          <Text style={styles.primaryButtonText}>Allow Camera Access</Text>
        </Pressable>
      </View>
    );
  }

  if (cameraOpen) {
    return (
      <View style={styles.cameraPage}>
        <CameraView ref={cameraRef} style={styles.camera} facing="back" />

        <View style={styles.cameraControls}>
          <Pressable style={styles.captureButton}>
            <Text style={styles.primaryButtonText}>Take Photo</Text>
          </Pressable>

          <Pressable style={styles.closeButton} onPress={() => setCameraOpen(false)}>
            <Text style={styles.closeButtonText}>Close Camera</Text>
          </Pressable>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.page}>
      <Text style={styles.logo}>EventLens</Text>
      <Text style={styles.title}>Graduation Party</Text>
      <Text style={styles.subtitle}>
        Add photos and videos from this event. Guests can upload memories using a QR code.
      </Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Add Media</Text>

        <Pressable style={styles.primaryButton}>
          <Text style={styles.primaryButtonText}>Upload Photo / Video</Text>
        </Pressable>

        <Pressable style={styles.secondaryButton} onPress={() => setCameraOpen(true)}>
          <Text style={styles.secondaryButtonText}>Open Camera</Text>
        </Pressable>

        <Pressable style={styles.secondaryButton}>
          <Text style={styles.secondaryButtonText}>View Gallery</Text>
        </Pressable>
      </View>

      <View style={styles.aiBox}>
        <Text style={styles.aiTitle}>AI Slideshow Prompt</Text>
        <Text style={styles.aiText}>
          Example: “Make a fun slideshow with the best group photos.”
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  page: {
    flex: 1,
    backgroundColor: '#F4F7FB',
    padding: 24,
    paddingTop: 90,
  },
  logo: {
    fontSize: 18,
    fontWeight: '700',
    color: '#2563EB',
    marginBottom: 12,
  },
  title: {
    fontSize: 34,
    fontWeight: '800',
    color: '#111827',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#6B7280',
    lineHeight: 24,
    marginBottom: 24,
  },
  card: {
    backgroundColor: 'white',
    padding: 22,
    borderRadius: 20,
    marginBottom: 18,
  },
  cardTitle: {
    fontSize: 22,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 18,
  },
  primaryButton: {
    backgroundColor: '#2563EB',
    paddingVertical: 16,
    borderRadius: 16,
    alignItems: 'center',
    marginBottom: 12,
  },
  primaryButtonText: {
    color: 'white',
    fontWeight: '700',
    fontSize: 16,
  },
  secondaryButton: {
    backgroundColor: '#EEF2FF',
    paddingVertical: 16,
    borderRadius: 16,
    alignItems: 'center',
    marginBottom: 12,
  },
  secondaryButtonText: {
    color: '#2563EB',
    fontWeight: '700',
    fontSize: 16,
  },
  aiBox: {
    backgroundColor: '#111827',
    padding: 20,
    borderRadius: 20,
  },
  aiTitle: {
    color: 'white',
    fontSize: 20,
    fontWeight: '700',
    marginBottom: 8,
  },
  aiText: {
    color: '#D1D5DB',
    fontSize: 15,
    lineHeight: 22,
  },
  cameraPage: {
    flex: 1,
    backgroundColor: '#000',
  },
  camera: {
    flex: 1,
  },
  cameraControls: {
    padding: 24,
    backgroundColor: '#111827',
  },
  captureButton: {
    backgroundColor: '#2563EB',
    paddingVertical: 16,
    borderRadius: 16,
    alignItems: 'center',
    marginBottom: 12,
  },
  closeButton: {
    backgroundColor: '#EEF2FF',
    paddingVertical: 16,
    borderRadius: 16,
    alignItems: 'center',
  },
  closeButtonText: {
    color: '#2563EB',
    fontWeight: '700',
    fontSize: 16,
  },
});