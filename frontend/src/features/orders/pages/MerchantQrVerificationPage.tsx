import { useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { getOrderRequest, updateOrderStatusRequest, validateQrCodeRequest } from '../../../api/orders'
import type { QRCodeValidationResponse } from '../../../types/orders'

const parseOrderId = (value: string): number | null => {
  const parsed = Number(value.trim())
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null
}

export function MerchantQrVerificationPage() {
  const queryClient = useQueryClient()
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const intervalRef = useRef<number | null>(null)
  const [isScannerOpen, setIsScannerOpen] = useState(false)
  const [qrDataInput, setQrDataInput] = useState('')
  const [orderIdInput, setOrderIdInput] = useState('')
  const [activeOrderId, setActiveOrderId] = useState<number | null>(null)
  const [verificationMessage, setVerificationMessage] = useState<string | null>(null)
  const [scanMessage, setScanMessage] = useState<string | null>('Open scanner to read a customer QR code.')

  const stopScanner = () => {
    if (intervalRef.current !== null) {
      window.clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop())
      streamRef.current = null
    }
    setIsScannerOpen(false)
  }

  const verifyQrMutation = useMutation({
    mutationFn: (qrData: string) => validateQrCodeRequest({ qr_data: qrData }),
    onSuccess: (response) => {
      setVerificationMessage(response.message)
      if (response.is_valid && response.order_id) {
        setActiveOrderId(response.order_id)
      } else {
        setActiveOrderId(null)
      }
    },
  })

  const resolveOrderMutation = useMutation({
    mutationFn: (orderId: number) =>
      validateQrCodeRequest({ qr_data: JSON.stringify({ type: 'order_pickup', order_id: orderId }) }),
    onSuccess: (response) => {
      setVerificationMessage(response.message)
      if (response.is_valid && response.order_id) {
        setActiveOrderId(response.order_id)
      } else {
        setActiveOrderId(null)
      }
    },
  })

  const selectedOrderQuery = useQuery({
    queryKey: ['merchant-verified-order', activeOrderId],
    queryFn: () => getOrderRequest(activeOrderId as number),
    enabled: activeOrderId !== null,
  })

  const completeOrderMutation = useMutation({
    mutationFn: (orderId: number) => updateOrderStatusRequest(orderId, { status: 'completed' }),
    onSuccess: (order) => {
      setVerificationMessage(`Order #${order.id} marked as completed.`)
      setActiveOrderId(order.id)
      void queryClient.invalidateQueries({ queryKey: ['orders'] })
      void queryClient.invalidateQueries({ queryKey: ['merchant-verified-order', order.id] })
    },
  })

  const primaryErrorMessage = useMemo(() => {
    const candidate = verifyQrMutation.error ?? resolveOrderMutation.error ?? completeOrderMutation.error ?? selectedOrderQuery.error
    return axios.isAxiosError<{ detail?: string }>(candidate)
      ? candidate.response?.data?.detail ?? 'Action failed. Try again.'
      : candidate
        ? 'Action failed. Try again.'
        : null
  }, [
    completeOrderMutation.error,
    resolveOrderMutation.error,
    selectedOrderQuery.error,
    verifyQrMutation.error,
  ])

  const selectedOrder = selectedOrderQuery.data

  const canComplete = selectedOrder?.status === 'ready' && !completeOrderMutation.isPending

  const applyVerificationResult = (response: QRCodeValidationResponse) => {
    setVerificationMessage(response.message)
    if (response.is_valid && response.order_id) {
      setActiveOrderId(response.order_id)
    } else {
      setActiveOrderId(null)
    }
  }

  const handleScan = async () => {
    if (typeof window === 'undefined' || !('BarcodeDetector' in window)) {
      setScanMessage('QR scan is not supported in this browser. Use QR payload or order ID.')
      return
    }

    if (!navigator.mediaDevices?.getUserMedia) {
      setScanMessage('Camera access is not available. Use QR payload or order ID.')
      return
    }

    try {
      const detector = new BarcodeDetector({ formats: ['qr_code'] })
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
      streamRef.current = stream
      setIsScannerOpen(true)
      setScanMessage('Point the camera at the QR code.')

      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }

      intervalRef.current = window.setInterval(async () => {
        const video = videoRef.current
        if (!video || video.readyState < 2) {
          return
        }

        try {
          const barcodes = await detector.detect(video)
          const value = barcodes[0]?.rawValue?.trim()
          if (!value) {
            return
          }

          setQrDataInput(value)
          stopScanner()
          const response = await validateQrCodeRequest({ qr_data: value })
          applyVerificationResult(response)
        } catch {
          setScanMessage('Unable to read QR yet. Keep camera steady.')
        }
      }, 500)
    } catch {
      stopScanner()
      setScanMessage('Camera access failed. Use QR payload or order ID.')
    }
  }

  const handleQrVerify = () => {
    const payload = qrDataInput.trim()
    if (!payload) {
      setVerificationMessage('Paste QR data first.')
      return
    }
    verifyQrMutation.mutate(payload)
  }

  const handleOrderIdVerify = () => {
    const parsedOrderId = parseOrderId(orderIdInput)
    if (!parsedOrderId) {
      setVerificationMessage('Enter a valid order ID.')
      return
    }
    resolveOrderMutation.mutate(parsedOrderId)
  }

  useEffect(() => () => stopScanner(), [])

  return (
    <section className="page-container merchant-qr-page">
      <header className="page-header">
        <h1>QR Verification</h1>
        <p>Scan customer QR or enter order ID to verify and complete pickup fast.</p>
      </header>

      <article className="store-card merchant-qr-panel">
        <h2>1) Scan QR</h2>
        <p className="muted-text">Use device camera when supported.</p>
        <div className="checkout-summary__actions">
          <button type="button" onClick={() => void handleScan()} disabled={isScannerOpen}>
            {isScannerOpen ? 'Scanning...' : 'Scan QR'}
          </button>
          {isScannerOpen ? (
            <button type="button" onClick={stopScanner}>
              Stop scanner
            </button>
          ) : null}
        </div>
        {scanMessage ? <p className="muted-text">{scanMessage}</p> : null}
        {isScannerOpen ? <video ref={videoRef} className="merchant-qr-video" autoPlay muted playsInline /> : null}
      </article>

      <article className="store-card merchant-qr-panel">
        <h2>2) Verify with QR data</h2>
        <div className="form-field">
          <label htmlFor="qr-data-input">QR payload</label>
          <textarea
            id="qr-data-input"
            className="form-input form-input--textarea"
            value={qrDataInput}
            onChange={(event) => setQrDataInput(event.target.value)}
            placeholder='{"type":"order_pickup","order_id":123}'
          />
        </div>
        <div className="checkout-summary__actions">
          <button type="button" onClick={handleQrVerify} disabled={verifyQrMutation.isPending}>
            {verifyQrMutation.isPending ? 'Verifying...' : 'Verify QR'}
          </button>
        </div>
      </article>

      <article className="store-card merchant-qr-panel">
        <h2>3) Or verify by order ID</h2>
        <div className="form-field">
          <label htmlFor="order-id-input">Order ID</label>
          <input
            id="order-id-input"
            className="form-input"
            inputMode="numeric"
            value={orderIdInput}
            onChange={(event) => setOrderIdInput(event.target.value)}
            placeholder="e.g. 123"
          />
        </div>
        <div className="checkout-summary__actions">
          <button type="button" onClick={handleOrderIdVerify} disabled={resolveOrderMutation.isPending}>
            {resolveOrderMutation.isPending ? 'Loading...' : 'Verify order ID'}
          </button>
        </div>
      </article>

      {verificationMessage ? (
        <article className="store-card">
          <p>{verificationMessage}</p>
        </article>
      ) : null}

      {primaryErrorMessage ? (
        <div className="inline-alert">
          <p>{primaryErrorMessage}</p>
        </div>
      ) : null}

      {selectedOrderQuery.isLoading ? <p>Loading verified order...</p> : null}

      {selectedOrder ? (
        <article className="store-card merchant-qr-result">
          <h2>Verified Order #{selectedOrder.id}</h2>
          <p className="muted-text">Status: {selectedOrder.status}</p>
          <p className="muted-text">Items: {selectedOrder.items.length}</p>
          <p className="muted-text">Total: ₦{Number(selectedOrder.total_amount).toLocaleString()}</p>
          <div className="checkout-summary__actions">
            <button
              type="button"
              onClick={() => completeOrderMutation.mutate(selectedOrder.id)}
              disabled={!canComplete}
            >
              {completeOrderMutation.isPending ? 'Completing...' : 'Mark as Completed'}
            </button>
          </div>
          {selectedOrder.status !== 'ready' ? (
            <p className="muted-text">Only READY orders can be marked as completed.</p>
          ) : null}
        </article>
      ) : null}
    </section>
  )
}
