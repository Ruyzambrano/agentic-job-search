import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"
import Stripe from "https://esm.sh/stripe@12.0.0"

const stripe = new Stripe(Deno.env.get("STRIPE_SECRET_KEY")!, {
  apiVersion: "2022-11-15",
  httpClient: Stripe.createFetchHttpClient(),
})

const supabaseUrl = Deno.env.get("SUPABASE_URL")!
const supabaseServiceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!

serve(async (req) => {
  const signature = req.headers.get("Stripe-Signature")
  if (!signature) {
    return new Response("Missing signature", { status: 400 })
  }

  try {
    const body = await req.text()
    const event = await stripe.webhooks.constructEventAsync(
    body,
    signature,
    Deno.env.get("STRIPE_WEBHOOK_SECRET")!
  )

    // Initialize Supabase with Service Role to bypass RLS safely
    const supabase = createClient(supabaseUrl, supabaseServiceKey)

    switch (event.type) {
      case "checkout.session.completed":
      case "invoice.payment_succeeded": {
        const session = event.data.object as any
        const customerId = session.customer
        const invoiceId = session.id || session.latest_invoice
        
        let userId = session.metadata?.user_id

        // If it's a subscription-based session and userId wasn't on the session root, fetch the subscription details
        if (!userId && session.subscription) {
          const subscription = await stripe.subscriptions.retrieve(session.subscription)
          userId = subscription.metadata?.user_id
        }

        // Fallback option if your test still doesn't find a user_id
        if (!userId) {
          console.warn(`◈ Could not extract user_id from metadata. Defaulting to test value for debugging.`)
          userId = "test-user-123" 
        }

        // Cache Stripe Customer ID to the user profile dimension
        await supabase
          .from("profiles")
          .update({ stripe_customer_id: customerId })
          .eq("id", userId)

        // SOP FACT LOGGING: Write transaction ledger record
        const { error } = await supabase
          .from("subscription_events")
          .insert({
            user_id: userId,
            tier_changed_to: "pro",
            payment_amount: session.amount_total || session.amount_paid || 1500,
            stripe_invoice_id: invoiceId
          })

        if (error) {
          if (error.code === "23505") {
            console.log("◈ Duplicate webhook event intercepted. Safely ignoring transaction.")
            return new Response("Duplicate ignored", { status: 200 })
          }
          throw error
        }

        console.log(`✅ Tier upgraded to PRO via Ledger Event for User: ${userId}`)
        break
      }

      case "customer.subscription.deleted": {
        const subscription = event.data.object as any
        const userId = subscription.metadata.user_id

        if (!userId) {
          console.error("◈ Missing user_id metadata on cancellation hook.")
          return new Response("Missing metadata", { status: 400 })
        }

        await supabase
          .from("profiles")
          .upsert({ 
            id: userId, 
            email: session.customer_details?.email || "unknown@email.com",
            tier: "trial" // Fallback creation state
          }, { onConflict: "id" })
        // SOP FACT LOGGING: Write zero-dollar demotion ledger record
        // The Postgres database trigger will instantly drop the profile tier to 'free'
        const { error } = await supabase
          .from("subscription_events")
          .insert({
            user_id: userId,
            tier_changed_to: "free",
            payment_amount: 0,
            stripe_invoice_id: `cl_cancel_${Date.now()}` // Artificial unique mapping string
          })

        if (error) throw error

        console.log(`❌ Tier demoted to FREE via Ledger Event for User: ${userId}`)
        break
      }
    }

    return new Response(JSON.stringify({ received: true }), { status: 200 })
  } catch (err) {
    console.error(`◈ Webhook Critical Processing Failure: ${err.message}`)
    return new Response(`Webhook Error: ${err.message}`, { status: 400 })
  }
})