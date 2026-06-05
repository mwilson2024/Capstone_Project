import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

export default function LibraryScreen() {
  return (
    <ScrollView style={styles.page}>
      <View style={styles.header}>
        <Text style={styles.logo}>EventLens</Text>
        <Text style={styles.title}>Your Event Library</Text>
        <Text style={styles.subtitle}>
          View your events, upload memories, and create AI-powered slideshows.
        </Text>
      </View>

      <EventCard emoji="🎓" title="Graduation Party" date="May 2026" photos="24 photos uploaded" />
      <EventCard emoji="💍" title="Wedding Reception" date="June 2026" photos="58 photos uploaded" />
      <EventCard emoji="🎂" title="Birthday Party" date="July 2026" photos="12 photos uploaded" />

      <Pressable style={styles.createButton}>
        <Text style={styles.createButtonText}>+ Create New Event</Text>
      </Pressable>
    </ScrollView>
  );
}

function EventCard({ emoji, title, date, photos }: any) {
  return (
    <View style={styles.card}>
      <View style={styles.thumbnail}>
        <Text style={styles.emoji}>{emoji}</Text>
      </View>

      <Text style={styles.cardTitle}>{title}</Text>
      <Text style={styles.date}>{date}</Text>
      <Text style={styles.cardText}>{photos}</Text>

      <Pressable style={styles.button}>
        <Text style={styles.buttonText}>Open Event</Text>
      </Pressable>
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
  header: {
    marginBottom: 24,
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
  },
  card: {
    backgroundColor: 'white',
    padding: 22,
    borderRadius: 24,
    marginBottom: 18,
    shadowColor: '#000',
    shadowOpacity: 0.08,
    shadowRadius: 14,
    shadowOffset: { width: 0, height: 6 },
  },
  thumbnail: {
    height: 130,
    backgroundColor: '#EEF2FF',
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 18,
  },
  emoji: {
    fontSize: 54,
  },
  cardTitle: {
    fontSize: 24,
    fontWeight: '800',
    color: '#111827',
    marginBottom: 4,
  },
  date: {
    fontSize: 15,
    color: '#2563EB',
    fontWeight: '700',
    marginBottom: 4,
  },
  cardText: {
    fontSize: 15,
    color: '#6B7280',
    marginBottom: 18,
  },
  button: {
    backgroundColor: '#2563EB',
    paddingVertical: 15,
    borderRadius: 16,
    alignItems: 'center',
  },
  buttonText: {
    color: 'white',
    fontWeight: '800',
    fontSize: 16,
  },
  createButton: {
    borderWidth: 2,
    borderColor: '#2563EB',
    paddingVertical: 18,
    borderRadius: 18,
    alignItems: 'center',
    marginTop: 10,
    marginBottom: 40,
  },
  createButtonText: {
    color: '#2563EB',
    fontWeight: '800',
    fontSize: 16,
  },
});