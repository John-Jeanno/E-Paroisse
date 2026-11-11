export type Announcement = {
    id: string;
    title: string;
    body: string;
    announcement_type?: string;
    published_at?: string;
    created_at?: string;
    link_url?: string;
    link_title?: string;
    image_url?: string;
    video_url?: string;
    media_url?: string;
    media_type?: 'image' | 'video' | '';
    comments_count?: number;
    likes_count?: number;
    shares_count?: number;
    is_liked?: boolean;
};
