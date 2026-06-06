import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import ExploreScreen from './explore';
import LoginScreen from './index';
import UploadScreen from './upload';

type Tab = 'home' | 'explore' | 'upload';

export default function RootLayout() {
  const [activeTab, setActiveTab] = useState<Tab>('home');

  const renderScreen = () => {
    switch (activeTab) {
      case 'home':
        return <LoginScreen />;
      case 'explore':
        return <ExploreScreen />;
      case 'upload':
        return <UploadScreen />;
    }
  };

  return (
    <SafeAreaProvider>
      <View style={styles.root}>
        {/* screen content fills all space above tab bar */}
        <View style={styles.screenArea}>{renderScreen()}</View>

        {/* Bottom Tab Bar */}
        <SafeAreaView edges={['bottom']} style={styles.tabBarWrapper}>
          <View style={styles.tabBar}> {/* using emojis for now since I do not have a better option for icons */}
            <TabItem
              label="Home"
              icon="🏠"
              active={activeTab === 'home'}
              onPress={() => setActiveTab('home')}
            />
            <TabItem
              label="Explore"
              icon="🗺️"
              active={activeTab === 'explore'}
              onPress={() => setActiveTab('explore')}
            />
            <TabItem
              label="Upload"
              icon="📷"
              active={activeTab === 'upload'}
              onPress={() => setActiveTab('upload')}
            />
          </View>
        </SafeAreaView>
      </View>
    </SafeAreaProvider>
  );
}

function TabItem({
  label,
  icon,
  active,
  onPress,
}: {
  label: string;
  icon: string;
  active: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable style={styles.tabItem} onPress={onPress}>
      <Text style={styles.tabIcon}>{icon}</Text>
      <Text style={[styles.tabLabel, active && styles.tabLabelActive]}>{label}</Text>
      {active && <View style={styles.activeIndicator} />}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: '#E8ECF0',
  },
  screenArea: {
    flex: 1,
  },
  tabBarWrapper: {
    backgroundColor: '#FFFFFF',
    borderTopWidth: 1,
    borderTopColor: '#DDE3EA',
  },
  tabBar: {
    flexDirection: 'row',
    height: 60,
    alignItems: 'center',
    justifyContent: 'space-around',
    paddingHorizontal: 8,
  },
  tabItem: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 8,
    position: 'relative',
  },
  tabIcon: {
    fontSize: 20,
    marginBottom: 2,
  },
  tabLabel: {
    fontSize: 11,
    fontWeight: '600',
    color: '#9CA3AF',
  },
  tabLabelActive: {
    color: '#2563EB',
  },
  activeIndicator: {
    position: 'absolute',
    top: 0,
    width: 28,
    height: 3,
    borderRadius: 2,
    backgroundColor: '#2563EB',
  },
});
