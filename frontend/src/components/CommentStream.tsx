import type { ProcessedComment } from '@/contracts/livecoach';
import { INTENT_LABELS, READINESS_LABELS, URGENCY_LABELS, formatTimestamp } from '@/features/replay/replayState';
import Icon from '@/components/Icon';

interface CommentStreamProps {
  comments: ProcessedComment[];
}

export default function CommentStream({ comments }: CommentStreamProps) {
  const newestFirst = [...comments].reverse();

  return (
    <section className="module comment-stream" aria-label="Komentar terbaru">
      <header className="module-header">
        <h2 className="section-heading"><Icon name="radio" size={14} />Aliran komentar</h2>
        <span className="section-meta">{comments.length > 0 ? `${comments.length} terbaru` : 'Menunggu data'}</span>
      </header>

      <div className="comment-list" aria-live="polite" aria-relevant="additions">
        {newestFirst.length === 0 ? (
          <div className="comment-empty">
            <div>
              <span className="empty-state-icon"><Icon name="radio" size={17} /></span>
              <strong>Menunggu komentar pertama</strong>
              <span>Mulai replay untuk melihat intent, kesiapan membeli, dan komentar yang perlu perhatian.</span>
            </div>
          </div>
        ) : (
          newestFirst.map((comment, index) => {
            const nlp = comment.nlp;
            const topIntent = [...nlp.intents].sort((a, b) => b.score - a.score)[0];
            const isNewest = index === 0;

            return (
              <article
                key={comment.entry.comment_id}
                className={isNewest ? 'comment-row animate-row-enter' : 'comment-row'}
                data-newest={isNewest}
                data-urgency={nlp.urgency}
              >
                <time className="comment-time">{formatTimestamp(comment.entry.timestamp_ms)}</time>
                <div className="comment-body">
                  <div className="comment-meta">
                    <span className="comment-intent" title={topIntent ? `${Math.round(topIntent.score * 100)}%` : undefined}>
                      {topIntent ? INTENT_LABELS[topIntent.intent] : 'Belum terklasifikasi'}
                    </span>
                    <span className="comment-flags">
                      {!nlp.usable_for_decision && <span className="confidence-marker" title="Confidence rendah; tidak digunakan untuk keputusan">Confidence rendah</span>}
                      {nlp.urgency !== 'NORMAL' && <span className="comment-urgency" data-level={nlp.urgency}>{URGENCY_LABELS[nlp.urgency]}</span>}
                      <span className="comment-readiness" data-level={nlp.readiness}>{READINESS_LABELS[nlp.readiness]}</span>
                    </span>
                  </div>
                  <p className="comment-text">{comment.entry.text}</p>
                </div>
              </article>
            );
          })
        )}
      </div>
    </section>
  );
}
