import { styles } from "./styles";
import React, { useEffect, useState } from "react";
import { Pressable, Text, View } from "react-native";
import { Image } from "expo-image";
import { Badge, s } from "../../../shared/ui";
import { dormLabel } from "../../location/@x/listing";
import { type Listing, priceLabel, statusLabel } from "../model/model";

const pictures = {
  yellow: require("../../../../assets/figma/yellow.svg"),
  blue: require("../../../../assets/figma/blue.svg"),
  brown: require("../../../../assets/figma/brown.svg"),
  sage: require("../../../../assets/figma/sage.svg"),
};

/** Показывает первую фотографию объявления либо заглушку, если фото отсутствует или недоступно. */
export function Picture({
  item,
  large = false,
  compact = false,
}: {
  item: Listing;
  large?: boolean;
  compact?: boolean;
}) {
  const [failed, setFailed] = useState(false);
  const uri = item.photos[0];
  useEffect(() => setFailed(false), [uri]);
  return (
    <View
      style={[
        styles.picture,
        large && styles.largePicture,
        compact && styles.compactPicture,
      ]}
    >
      <Image
        source={uri && !failed ? { uri } : pictures[item.color]}
        style={styles.absoluteFill}
        contentFit="cover"
        loading="eager"
        onError={() => setFailed(true)}
        accessibilityLabel={`Фото: ${item.title}`}
      />
      {uri && failed && <Text style={styles.imageFallback}>Фото недоступно</Text>}
    </View>
  );
}

/** Показывает карточку объявления с форматом, ценой или статусом и обработчиком открытия. */
export function Card({ item, own = false, onPress }: { item: Listing; own?: boolean; onPress: () => void; }) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`${item.title}, ${priceLabel(item)}`}
      onPress={onPress}
      style={({ pressed }) => [styles.card, pressed && styles.pressedCard]}
    >
      <View>
        <Picture item={item} />
        <View style={s.badgePosition}>
          <Badge text={item.format} />
        </View>
      </View>
      <View style={styles.cardCopy}>
        <Text numberOfLines={2} style={s.cardTitle}>
          {item.title}
        </Text>
        <Text numberOfLines={1} style={s.small}>
          {own ? statusLabel[item.status] : priceLabel(item)}
        </Text>
        <Text numberOfLines={1} style={[s.small, styles.locationText]}>
          {dormLabel(item.dorm)}
        </Text>
      </View>
    </Pressable>
  );
}
