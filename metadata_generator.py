from typing import Dict, List

class MetadataGenerator:
    """Generate professional YouTube metadata for type beat videos"""
    
    def generate_metadata(self, artist_type: str, beat_name: str, purchase_link: str = "", producer_name: str = "Producer") -> Dict:
        """Generate title, description, and tags for YouTube video"""
        
        # Create professional title
        title = f"[FREE] {artist_type} Type Beat - \"{beat_name}\""
        
        # Generate comprehensive tags
        tags = self._generate_tags(artist_type, producer_name)
        
        # Create professional description
        description = self._generate_description(artist_type, beat_name, purchase_link, tags)
        
        return {
            "title": title,
            "description": description,
            "tags": tags
        }
    
    def _generate_tags(self, artist_type: str, producer_name: str) -> List[str]:
        """Generate comprehensive tags for better discoverability"""
        artist_lower = artist_type.lower()
        producer_lower = producer_name.lower()
        
        tags = [
            producer_lower,
            f"{artist_lower} type beat",
            f"free {artist_lower} type beat",
            f"{artist_lower} type beat 2025",
            f"free {artist_lower} type beat 2025",
            "type beat",
            "free type beat",
            "type beat 2025",
            "free type beat 2025",
            "beat",
            "beats",
            "type beats",
            "free type beats",
            "instrumental",
            "free instrumental",
            "rap beat",
            "hip hop beat",
            "trap beat",
            "free beat",
            "beats to rap to",
            "rap instrumental"
        ]
        
        # Add variations
        if " " in artist_type:
            # Add version without spaces
            artist_nospace = artist_type.replace(" ", "").lower()
            tags.extend([
                f"{artist_nospace} type beat",
                f"free {artist_nospace} type beat"
            ])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_tags = []
        for tag in tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)
        
        return unique_tags[:50]  # YouTube allows max 500 characters for tags
    
    def _generate_description(self, artist_type: str, beat_name: str, purchase_link: str, tags: List[str]) -> str:
        """Generate professional YouTube description"""
        
        # Create tags string for description
        tags_text = ",".join(tags[:20])  # First 20 tags for description
        
        # Create hashtags
        artist_hashtag = artist_type.lower().replace(" ", "").replace("-", "")
        hashtags = f"#{artist_hashtag}typebeat #typebeat #freetypebeat #beats #instrumental"
        
        # Purchase link section
        purchase_section = ""
        if purchase_link:
            purchase_section = f"💰 Purchase This Beat (Untagged) | {purchase_link}\n\n"
        else:
            purchase_section = "💰 Purchase This Beat (Untagged) | [Add your beat store link]\n\n"
        
        # Full description template
        description = f"""{purchase_section}Connect with me:
📧 Email | [Add your email]
📱 Instagram | [Add your Instagram]
💰 Beat Store | [Add your beat store]
🎵 YouTube | [Add your YouTube channel]

[FREE] {artist_type} Type Beat - "{beat_name}"

This is a FREE type beat inspired by {artist_type}'s style. Perfect for artists looking for high-quality instrumentals to create their next hit!

🎤 FREE FOR NON-PROFIT USE
💰 Purchase a license for commercial use
🎧 Download link in bio

Tags: {tags_text}

{hashtags}

#music #hiphop #rap #producer #beatmaker #typebeats #freebeats"""
        
        return description