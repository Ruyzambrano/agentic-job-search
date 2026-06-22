import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import Stripe from 'https://esm.sh/stripe@11.1.0'

const stripe = new Stripe(Deno.env.get('STRIPE_SECRET_KEY') as string, {
  apiVersion: '2022-11-15',
  httpClient: Stripe.createFetchHttpClient(),
})

serve(async (req) => {
  const signature = req.headers.get('stripe-signature')

  try {
    const body = await req.text()
    const event = stripe.webhooks.constructEvent(
      body,
      signature!,
      Deno.env.get('STRIPE_WEBHOOK_SECRET') as string
    )

  const supabase = createClient(
    Deno.env.get('SUPABASE_URL') as string,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') as string // This one is auto-filled by Supabase
  )

    // 1. HANDLE SUCCESSFUL PAYMENT
    if (event.type === 'checkout.session.completed') {
      const session = event.data.object
      const userEmail = session.customer_details.email
      const stripeCustomerId = session.customer

      console.log(`🔔 Payment successful for ${userEmail}`)

      const { error } = await supabase
        .from('profiles')
        .update({ 
          is_pro: true,
          stripe_customer_id: stripeCustomerId 
        })
        .eq('email', userEmail)

      if (error) throw error
    }

    if (event.type === 'customer.subscription.deleted') {
      const subscription = event.data.object
      const stripeCustomerId = subscription.customer

      console.log(`❌ Subscription ended for customer: ${stripeCustomerId}`)

      const { error } = await supabase
        .from('profiles')
        .update({ is_pro: false })
        .eq('stripe_customer_id', stripeCustomerId)

      if (error) throw error
    }

    return new Response(JSON.stringify({ received: true }), { status: 200 })
  } catch (err) {
    console.error(`Webhook Error: ${err.message}`)
    return new Response(`Webhook Error: ${err.message}`, { status: 400 })
  }
})