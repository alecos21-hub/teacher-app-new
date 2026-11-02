matched_student = class_students[i % len(class_students)] if class_students else f"Student_{i+1}"
                                score_val = 50
                                feedback_val = "Χωρίς σχόλιο."
                                
                                if resp_text:
                                    # 1. Προσπάθεια εξαγωγής JSON
                                    clean_resp = resp_text.replace("```json", "").replace("```", "").strip()
                                    json_match = re.search(r'\{.*\}', clean_resp, re.DOTALL)
                                    if json_match:
                                        try:
                                            res_data = json.loads(json_match.group(0))
                                            raw_name = str(res_data.get("student_name", ""))
                                            for s in class_students:
                                                if s.lower() in raw_name.lower() or raw_name.lower() in s.lower():
                                                    matched_student = s
                                                    break
                                            score_val = int(res_data.get("score", 50))
                                            feedback_val = str(res_data.get("feedback", "Χωρίς σχόλιο."))
                                        except:
                                            pass
                                    
                                    # 2. Αν απέτυχε το JSON, ψάχνουμε απευθείας για αριθμούς βαθμολογίας στο κείμενο
                                    if score_val == 50 and resp_text:
                                        nums = re.findall(r'\b(100|[1-9]?[0-9])\b', resp_text)
                                        if nums:
                                            # Παίρνουμε τον πρώτο λογικό βαθμό που θα βρει (αποφεύγοντας τυχόν ημερομηνίες)
                                            for n in nums:
                                                val = int(n)
                                                if val <= 100:
                                                    score_val = val
                                                    break
                                        feedback_val = resp_text[:200] # Κρατάμε το feedback από το AI
