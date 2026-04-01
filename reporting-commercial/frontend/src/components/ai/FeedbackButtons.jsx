import { useState } from 'react'
import { ThumbsUp, ThumbsDown } from 'lucide-react'
import { useChat } from '../../context/ChatContext'

export default function FeedbackButtons({ question, sqlQuery, messageId }) {
  const { submitFeedback } = useChat()
  const [rating, setRating] = useState(null) // null | 'positive' | 'negative'
  const [submitted, setSubmitted] = useState(false)

  if (!question) return null

  const handleFeedback = async (newRating) => {
    if (submitted) return
    setRating(newRating)
    setSubmitted(true)
    await submitFeedback(question, sqlQuery || '', newRating)
  }

  return (
    <div className="ml-10 mt-1 flex items-center gap-1.5">
      <span className="text-[10px] text-gray-400 dark:text-gray-500">
        {submitted ? 'Merci pour votre retour !' : 'Cette réponse était-elle utile ?'}
      </span>
      {!submitted && (
        <>
          <button
            onClick={() => handleFeedback('positive')}
            title="Réponse utile"
            className="p-1 rounded-md text-gray-400 hover:text-green-500 hover:bg-green-50 dark:hover:bg-green-900/20 transition-colors"
          >
            <ThumbsUp className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => handleFeedback('negative')}
            title="Réponse à améliorer"
            className="p-1 rounded-md text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
          >
            <ThumbsDown className="w-3.5 h-3.5" />
          </button>
        </>
      )}
      {submitted && rating === 'positive' && (
        <ThumbsUp className="w-3.5 h-3.5 text-green-500" />
      )}
      {submitted && rating === 'negative' && (
        <ThumbsDown className="w-3.5 h-3.5 text-red-500" />
      )}
    </div>
  )
}
