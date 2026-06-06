import { useState } from 'react';
import {
  Dimensions,
  FlatList,
  Image,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const GRID_PADDING = 16;
const CELL_MARGIN = 2;
const PHOTO_SIZE = Math.floor((SCREEN_WIDTH - GRID_PADDING * 2 - CELL_MARGIN * 4) / 3);

const EVENT_PHOTOS: Record<string, { id: string; uri: string; caption: string }[]> = {
  'Graduation Party': [
    { id: '1', uri: 'https://picsum.photos/seed/grad1/400/400', caption: 'Cap & Gown' },
    { id: '2', uri: 'https://picsum.photos/seed/grad2/400/400', caption: 'Group Selfie' },
    { id: '3', uri: 'https://picsum.photos/seed/grad3/400/400', caption: 'Family Photo' },
    { id: '4', uri: 'https://picsum.photos/seed/grad4/400/400', caption: 'Diploma Moment' },
    { id: '5', uri: 'https://picsum.photos/seed/grad5/400/400', caption: 'Celebration!' },
    { id: '6', uri: 'https://picsum.photos/seed/grad6/400/400', caption: 'Friends Forever' },
    { id: '7', uri: 'https://picsum.photos/seed/grad7/400/400', caption: 'Toast Time' },
    { id: '8', uri: 'https://picsum.photos/seed/grad8/400/400', caption: 'Party Vibes' },
    { id: '9', uri: 'https://picsum.photos/seed/grad9/400/400', caption: 'Sunset Shot' },
  ],
  'Wedding Reception': [
    { id: '1', uri: 'https://picsum.photos/seed/wed1/400/400', caption: 'First Dance' },
    { id: '2', uri: 'https://picsum.photos/seed/wed2/400/400', caption: 'The Vows' },
    { id: '3', uri: 'https://picsum.photos/seed/wed3/400/400', caption: 'Cake Cutting' },
    { id: '4', uri: 'https://picsum.photos/seed/wed4/400/400', caption: 'Bouquet Toss' },
    { id: '5', uri: 'https://picsum.photos/seed/wed5/400/400', caption: 'Table Decor' },
    { id: '6', uri: 'https://picsum.photos/seed/wed6/400/400', caption: 'Bridal Party' },
    { id: '7', uri: 'https://picsum.photos/seed/wed7/400/400', caption: 'Sunset Portraits' },
    { id: '8', uri: 'https://picsum.photos/seed/wed8/400/400', caption: 'Dance Floor' },
  ],
  'Birthday Party': [
    { id: '1', uri: 'https://picsum.photos/seed/bday1/400/400', caption: 'Birthday Cake' },
    { id: '2', uri: 'https://picsum.photos/seed/bday2/400/400', caption: 'Blowing Candles' },
    { id: '3', uri: 'https://picsum.photos/seed/bday3/400/400', caption: 'Gift Opening' },
    { id: '4', uri: 'https://picsum.photos/seed/bday4/400/400', caption: 'Party Games' },
    { id: '5', uri: 'https://picsum.photos/seed/bday5/400/400', caption: 'Group Photo' },
  ],
};

type Photo = { id: string; uri: string; caption: string };
type EventItem = { emoji: string; title: string; date: string; photos: string };

const EVENTS: EventItem[] = [
  { emoji: '🎓', title: 'Graduation Party', date: 'May 2026', photos: '24 photos uploaded' },
  { emoji: '💍', title: 'Wedding Reception', date: 'June 2026', photos: '58 photos uploaded' },
  { emoji: '🎂', title: 'Birthday Party', date: 'July 2026', photos: '12 photos uploaded' },
];

export default function LibraryScreen() {
  const [openEvent, setOpenEvent] = useState<EventItem | null>(null);
  const [lightboxPhoto, setLightboxPhoto] = useState<Photo | null>(null);
  if (openEvent) {
    const photos = EVENT_PHOTOS[openEvent.title] ?? [];
    return (
      <GalleryScreen
        event={openEvent}
        photos={photos}
        lightboxPhoto={lightboxPhoto}
        onOpenPhoto={setLightboxPhoto}
        onCloseLightbox={() => setLightboxPhoto(null)}
        onBack={() => setOpenEvent(null)}
      />
    );
  }
  return (
    <ScrollView style={styles.page} contentContainerStyle={styles.pageContent}>
      <View style={styles.header}>
        <Text style={styles.logo}>EventLens</Text>
        <Text style={styles.title}>Your Event Library</Text>
        <Text style={styles.subtitle}>View your events, upload memories, and create AI-powered slideshows.</Text>
      </View>
      {EVENTS.map((event) => (
        <EventCard key={event.title} event={event} onOpen={() => setOpenEvent(event)} />
      ))}
      <Pressable style={styles.createButton}>
        <Text style={styles.createButtonText}>+ Create New Event</Text>
      </Pressable>
    </ScrollView>
  );
}

function EventCard({ event, onOpen }: { event: EventItem; onOpen: () => void }) {
  return (
    <View style={styles.card}>
      <View style={styles.thumbnail}>
        <Text style={styles.emoji}>{event.emoji}</Text>
      </View>
      <Text style={styles.cardTitle}>{event.title}</Text>
      <Text style={styles.date}>{event.date}</Text>
      <Text style={styles.cardText}>{event.photos}</Text>
      <Pressable style={styles.button} onPress={onOpen}>
        <Text style={styles.buttonText}>Open Event</Text>
      </Pressable>
    </View>
  );
}

function GalleryScreen({
  event,
  photos,
  lightboxPhoto,
  onOpenPhoto,
  onCloseLightbox,
  onBack,
}: {
  event: EventItem;
  photos: Photo[];
  lightboxPhoto: Photo | null;
  onOpenPhoto: (p: Photo) => void;
  onCloseLightbox: () => void;
  onBack: () => void;
}) {
  const metaText = event.date + ' - ' + String(photos.length) + ' photos';
  const lightboxUri = lightboxPhoto ? lightboxPhoto.uri.replace('/400/400', '/800/800') : 'https://picsum.photos/seed/placeholder/800/800';
  const lightboxCaption = lightboxPhoto ? lightboxPhoto.caption : '';
  return (
    <View style={styles.galleryPage}>
      <View style={styles.galleryHeader}>
        <Pressable style={styles.backButton} onPress={onBack}>
          <Text style={styles.backArrow}>{'<- '}</Text>
          <Text style={styles.backLabel}>Library</Text>
        </Pressable>
        <View style={styles.galleryTitleRow}>
          <Text style={styles.galleryEmoji}>{event.emoji}</Text>
          <Text style={styles.galleryTitle}>{event.title}</Text>
        </View>
        <Text style={styles.galleryMeta}>{metaText}</Text>
      </View>
      <FlatList
        data={photos}
        keyExtractor={(item) => item.id}
        numColumns={3}
        contentContainerStyle={styles.grid}
        columnWrapperStyle={styles.gridRow}
        renderItem={({ item }) => (
          <Pressable onPress={() => onOpenPhoto(item)} style={styles.gridCell}>
            <Image source={{ uri: item.uri }} style={styles.gridImage} />
          </Pressable>
        )}
      />
      <Modal visible={lightboxPhoto !== null} transparent animationType="fade">
        <View style={styles.lightboxBg}>
          <Pressable style={styles.lightboxClose} onPress={onCloseLightbox}>
            <Text style={styles.lightboxCloseText}>X</Text>
          </Pressable>
          <Image source={{ uri: lightboxUri }} style={styles.lightboxImage} resizeMode="contain" />
          <Text style={styles.lightboxCaption}>{lightboxCaption}</Text>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  page: {
    flex: 1,
    backgroundColor: '#E8ECF0',
  },
  pageContent: {
    padding: 24,
    paddingTop: 60,
    paddingBottom: 32,
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
    shadowOpacity: 0.07,
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
  },
  createButtonText: {
    color: '#2563EB',
    fontWeight: '800',
    fontSize: 16,
  },
  galleryPage: {
    flex: 1,
    backgroundColor: '#E8ECF0',
  },
  galleryHeader: {
    backgroundColor: '#FFFFFF',
    paddingTop: 56,
    paddingBottom: 18,
    paddingHorizontal: 24,
    borderBottomWidth: 1,
    borderBottomColor: '#DDE3EA',
  },
  backButton: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 14,
  },
  backArrow: {
    fontSize: 16,
    color: '#2563EB',
    fontWeight: '700',
  },
  backLabel: {
    fontSize: 15,
    color: '#2563EB',
    fontWeight: '600',
  },
  galleryTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  galleryEmoji: {
    fontSize: 28,
    marginRight: 10,
  },
  galleryTitle: {
    fontSize: 26,
    fontWeight: '800',
    color: '#111827',
  },
  galleryMeta: {
    fontSize: 14,
    color: '#6B7280',
    fontWeight: '500',
  },
  grid: {
    padding: GRID_PADDING,
    paddingBottom: 32,
  },
  gridRow: {
    justifyContent: 'space-between',
    marginBottom: CELL_MARGIN * 2,
  },
  gridCell: {
    width: PHOTO_SIZE,
    height: PHOTO_SIZE,
    borderRadius: 10,
    overflow: 'hidden',
    backgroundColor: '#DDE3EA',
  },
  gridImage: {
    width: '100%',
    height: '100%',
  },
  lightboxBg: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.93)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  lightboxClose: {
    position: 'absolute',
    top: 52,
    right: 20,
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(255,255,255,0.15)',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 10,
  },
  lightboxCloseText: {
    color: 'white',
    fontSize: 17,
    fontWeight: '700',
  },
  lightboxImage: {
    width: SCREEN_WIDTH,
    height: SCREEN_WIDTH,
  },
  lightboxCaption: {
    color: '#D1D5DB',
    fontSize: 15,
    marginTop: 18,
    fontWeight: '500',
  },
});
