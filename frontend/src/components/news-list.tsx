"use client";

import { Newspaper } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { NewsArticleResponse } from "@/lib/api";

interface NewsListProps {
  articles: NewsArticleResponse[];
}

export function NewsList({ articles }: NewsListProps) {
  if (articles.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground text-sm">
          Chưa có tin tức cho mã này.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Newspaper className="size-4" />
          Tin tức gần đây
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {articles.map((article, i) => (
          <a
            key={`${article.url}-${i}`}
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-start gap-3 p-2 -mx-2 rounded-md hover:bg-muted/50 transition-colors group"
          >
            <div className="flex-1 min-w-0">
              <p className="text-sm leading-snug group-hover:text-primary transition-colors line-clamp-2">
                {article.title}
              </p>
              <p className="text-[10px] text-muted-foreground/60 mt-1">
                {new Date(article.published_at).toLocaleDateString("vi-VN", {
                  day: "2-digit",
                  month: "2-digit",
                  year: "numeric",
                })}
              </p>
            </div>
          </a>
        ))}
      </CardContent>
    </Card>
  );
}
