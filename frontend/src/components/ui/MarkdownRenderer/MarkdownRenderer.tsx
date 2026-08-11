"use client";

import "highlight.js/styles/github.css";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export function MarkdownRenderer({ content, className = "" }: MarkdownRendererProps) {
  return (
    <div className={`markdown-content ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          // Custom table styling
          table: ({ children, ...props }) => (
            <div className="overflow-x-auto my-4">
              <table
                className="min-w-full border-collapse border border-gray-300 bg-white shadow-sm"
                {...props}
              >
                {children}
              </table>
            </div>
          ),
          thead: ({ children, ...props }) => (
            <thead className="bg-gray-50" {...props}>
              {children}
            </thead>
          ),
          tbody: ({ children, ...props }) => (
            <tbody className="divide-y divide-gray-200" {...props}>
              {children}
            </tbody>
          ),
          tr: ({ children, ...props }) => (
            <tr className="hover:bg-gray-50" {...props}>
              {children}
            </tr>
          ),
          th: ({ children, ...props }) => (
            <th
              className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b border-gray-300"
              {...props}
            >
              {children}
            </th>
          ),
          td: ({ children, ...props }) => (
            <td
              className="px-4 py-3 text-sm text-gray-900 border-b border-gray-200"
              {...props}
            >
              {children}
            </td>
          ),
          // Custom heading styling
          h1: ({ children, ...props }) => (
            <h1
              className="text-2xl font-bold text-gray-900 mt-6 mb-4 first:mt-0"
              {...props}
            >
              {children}
            </h1>
          ),
          h2: ({ children, ...props }) => (
            <h2
              className="text-xl font-semibold text-gray-900 mt-5 mb-3 first:mt-0"
              {...props}
            >
              {children}
            </h2>
          ),
          h3: ({ children, ...props }) => (
            <h3
              className="text-lg font-medium text-gray-900 mt-4 mb-2 first:mt-0"
              {...props}
            >
              {children}
            </h3>
          ),
          h4: ({ children, ...props }) => (
            <h4
              className="text-base font-medium text-gray-900 mt-3 mb-2 first:mt-0"
              {...props}
            >
              {children}
            </h4>
          ),
          // Custom paragraph styling
          p: ({ children, ...props }) => (
            <p
              className="text-sm leading-relaxed text-gray-900 mb-3 last:mb-0"
              {...props}
            >
              {children}
            </p>
          ),
          // Custom list styling
          ul: ({ children, ...props }) => (
            <ul
              className="list-disc list-inside space-y-1 mb-3 text-sm text-gray-900"
              {...props}
            >
              {children}
            </ul>
          ),
          ol: ({ children, ...props }) => (
            <ol
              className="list-decimal list-inside space-y-1 mb-3 text-sm text-gray-900"
              {...props}
            >
              {children}
            </ol>
          ),
          li: ({ children, ...props }) => (
            <li className="text-sm text-gray-900" {...props}>
              {children}
            </li>
          ),
          // Custom code styling
          code: ({ children, className, ...props }) => {
            const isInline = !className;
            if (isInline) {
              return (
                <code
                  className="bg-gray-100 text-gray-800 px-1.5 py-0.5 rounded text-xs font-mono"
                  {...props}
                >
                  {children}
                </code>
              );
            }
            return (
              <code className={className} {...props}>
                {children}
              </code>
            );
          },
          pre: ({ children, ...props }) => (
            <pre
              className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm font-mono my-4"
              {...props}
            >
              {children}
            </pre>
          ),
          // Custom blockquote styling
          blockquote: ({ children, ...props }) => (
            <blockquote
              className="border-l-4 border-gray-300 pl-4 py-2 my-4 bg-gray-50 text-gray-700 italic"
              {...props}
            >
              {children}
            </blockquote>
          ),
          // Custom strong/bold styling
          strong: ({ children, ...props }) => (
            <strong className="font-semibold text-gray-900" {...props}>
              {children}
            </strong>
          ),
          // Custom emphasis/italic styling
          em: ({ children, ...props }) => (
            <em className="italic text-gray-700" {...props}>
              {children}
            </em>
          ),
          // Custom horizontal rule
          hr: ({ ...props }) => <hr className="border-gray-300 my-6" {...props} />,
          // Custom link styling
          a: ({ children, href, ...props }) => (
            <a
              className="text-blue-600 hover:text-blue-800 underline"
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              {...props}
            >
              {children}
            </a>
          ),
          // Custom image styling
          img: ({ src, alt, ...props }) => (
            <img
              className="max-w-full h-auto rounded-lg shadow-sm my-4"
              src={src}
              alt={alt}
              {...props}
            />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
