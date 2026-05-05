"use client";

import type { RumorPost } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MessageCircle, ThumbsUp, Reply, BadgeCheck } from "lucide-react";

interface RumorFeedProps {
  posts: RumorPost[];
}

export function RumorFeed({ posts }: RumorFeedProps) {
  if (posts.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground text-sm">
          Chưa có bài viết
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <MessageCircle className="size-4" />
          Bài viết cộng đồng
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        {posts.map((post, i) => (
          <div key={i} className="p-3 border-b last:border-b-0">
            {/* Author */}
            <div className="flex items-center gap-1 mb-1">
              <span className="text-xs font-medium">{post.author_name}</span>
              {post.is_authentic && (
                <BadgeCheck className="size-3 text-blue-500" />
              )}
            </div>

            {/* Content */}
            <p className="text-sm leading-snug line-clamp-3">
              {post.content}
            </p>

            {/* Footer: likes, replies, date */}
            <div className="flex items-center gap-3 mt-1.5 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <ThumbsUp className="size-3" />
                {post.total_likes}
              </span>
              <span className="flex items-center gap-1">
                <Reply className="size-3" />
                {post.total_replies}
              </span>
              <span>
                {new Date(post.posted_at).toLocaleDateString("vi-VN")}
              </span>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
