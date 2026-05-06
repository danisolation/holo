"use client";

import type { RumorPost } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MessageCircle, ThumbsUp, Reply, BadgeCheck, Newspaper, Radio, Globe, Users } from "lucide-react";

interface RumorFeedProps {
  posts: RumorPost[];
}

type SourceInfo = {
  label: string;
  color: string;
  icon: React.ReactNode;
};

function getSourceInfo(authorName: string): SourceInfo {
  if (authorName.startsWith("tg:")) {
    return { label: "Telegram", color: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300", icon: <Radio className="size-3" /> };
  }
  if (authorName.startsWith("tnck:")) {
    return { label: "TNCK", color: "bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300", icon: <Newspaper className="size-3" /> };
  }
  if (authorName.startsWith("ndt:")) {
    return { label: "NhaDauTu", color: "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300", icon: <Newspaper className="size-3" /> };
  }
  if (authorName.startsWith("vnexpress") || authorName.startsWith("vietstock")) {
    return { label: authorName.split(":")[0] || authorName, color: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300", icon: <Newspaper className="size-3" /> };
  }
  if (authorName.includes("f319") || authorName.startsWith("F319")) {
    return { label: "F319", color: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300", icon: <Users className="size-3" /> };
  }
  // Default: Fireant / community
  return { label: "Fireant", color: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300", icon: <Globe className="size-3" /> };
}

function getDisplayName(authorName: string): string {
  // Strip source prefix for display
  if (authorName.startsWith("tg:") || authorName.startsWith("ndt:") || authorName.startsWith("tnck:")) {
    return authorName.split(":").slice(1).join(":");
  }
  return authorName;
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
        {posts.map((post, i) => {
          const source = getSourceInfo(post.author_name);
          return (
            <div key={i} className="p-3 border-b last:border-b-0">
              {/* Author + Source Badge */}
              <div className="flex items-center gap-1.5 mb-1">
                <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium ${source.color}`}>
                  {source.icon}
                  {source.label}
                </span>
                <span className="text-xs font-medium">{getDisplayName(post.author_name)}</span>
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
          );
        })}
      </CardContent>
    </Card>
  );
}
