class VoiceService:
    def process_command(self, command_text):
        command_text = command_text.lower()
        
        if "حالة" in command_text or "status" in command_text:
            if "الذهب" in command_text or "gold" in command_text:
                return "Gold is currently in a bullish trend, approaching resistance at 2350."
            return "Markets are stable today with low volatility."
            
        if "حلل" in command_text or "analyze" in command_text:
            if "اليورو" in command_text or "euro" in command_text:
                return "EUR/USD analysis: Strong support at 1.0850, looking for buy opportunities."
            return "Please specify an asset to analyze."
            
        if "توصية" in command_text or "recommendation" in command_text:
            return "Last recommendation: Buy XAU/USD at 2340, TP 2360, SL 2330."
            
        return "I didn't understand the command. Try 'Analyze Gold' or 'Market Status'."
