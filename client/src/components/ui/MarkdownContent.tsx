import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "../../utils/cn";

interface MarkdownContentProps {
  content: string;
  className?: string;
}

export const MarkdownContent: React.FC<MarkdownContentProps> = ({
  content,
  className,
}) => {
  return (
    <div
      className={cn(
        "prose prose-sm max-w-none",
        "prose-headings:font-semibold prose-headings:text-gray-900",
        "prose-p:text-gray-900 prose-p:leading-relaxed",
        "prose-a:text-blue-600 prose-a:no-underline hover:prose-a:underline",
        "prose-strong:text-gray-900 prose-strong:font-semibold",
        "prose-code:text-gray-900 prose-code:bg-gray-100 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-code:font-mono",
        "prose-pre:bg-gray-900 prose-pre:text-gray-100 prose-pre:rounded-lg prose-pre:p-4",
        "prose-blockquote:border-l-4 prose-blockquote:border-gray-300 prose-blockquote:pl-4 prose-blockquote:text-gray-600",
        "prose-ul:list-disc prose-ol:list-decimal",
        "prose-li:text-gray-900",
        "prose-table:border-collapse prose-table:border prose-table:border-gray-300",
        "prose-th:border prose-th:border-gray-300 prose-th:bg-gray-50 prose-th:p-2 prose-th:text-left prose-th:font-semibold",
        "prose-td:border prose-td:border-gray-300 prose-td:p-2",
        className
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Custom code block styling
          code: ({ node, className, children, ...props }) => {
            const match = /language-(\w+)/.exec(className || "");
            const isInline = !match;

            return isInline ? (
              <code
                className="bg-gray-100 text-gray-900 px-1 py-0.5 rounded text-sm font-mono"
                {...props}
              >
                {children}
              </code>
            ) : (
              <pre className="bg-gray-900 text-gray-100 rounded-lg p-4 overflow-x-auto">
                <code className={className} {...props}>
                  {children}
                </code>
              </pre>
            );
          },
          // Custom link styling
          a: ({ children, href, ...props }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:underline"
              {...props}
            >
              {children}
            </a>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};
