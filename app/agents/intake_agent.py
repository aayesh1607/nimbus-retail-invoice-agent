from app.models.invoice import Invoice
from app.models.packets import InvoicePacket


class InvoiceIntakeAgent:

    def __init__(self):
        self.agent_name = "intake_agent"

    def receive_invoice(self, invoice: Invoice) -> InvoicePacket:
        """
        Receive an invoice and create its initial processing packet.
        """

        packet = InvoicePacket(
            invoice=invoice,
            current_agent=self.agent_name
        )

        print(
            f"Invoice {invoice.invoice_id} received successfully."
        )

        return packet