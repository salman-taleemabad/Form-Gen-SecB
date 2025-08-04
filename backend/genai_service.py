import openai
import json
import os
from typing import Dict, Any, Optional, Tuple
from tenacity import retry, wait_random_exponential, stop_after_attempt
from backend.single_prompt_template import SINGLE_PROMPT_TEMPLATE

class GenAIService:
    @classmethod
    @retry(
        wait=wait_random_exponential(min=1, max=60),
        stop=stop_after_attempt(6),
        reraise=True,
    )
    def get_completion(
        cls,
        api_key: Optional[str] = None,
        organization: Optional[str] = None,
        prompt: str = "",
        messages: Optional[list] = None,
        images: list = [],
        model: str = "gpt-4o",
        json_mode: bool = True,
        serializer: Optional[Any] = None,
        serializer_validation_data: Dict[str, Any] = {},
        max_tokens: int = 4096,
    ) -> Tuple[Any, Dict[str, int]]:
        """
        Get completion from OpenAI API using single prompt approach (matching teammate's method)
        """
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            raise Exception("OpenAI API key not found")
        
        # Set the API key
        openai.api_key = api_key
        if organization:
            openai.organization = organization
        
        try:
            # Use single prompt approach (no separate system/user messages)
            print(f"🔍 DEBUG: Making OpenAI API call with model: {model}")
            response = openai.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=max_tokens,
                response_format={"type": "json_object"} if json_mode else None,
            )
            
            response_content = response.choices[0].message.content
            print(f"🔍 DEBUG: Raw OpenAI response content: {response_content}")
            
            tokens_used = {
                "input_tokens_used": response.usage.prompt_tokens,
                "output_tokens_used": response.usage.completion_tokens,
                "total_tokens_used": response.usage.total_tokens
            }
            
            print(
                f"Tokens Used -> Input: {tokens_used.get('input_tokens_used')} "
                f"Output: {tokens_used.get('output_tokens_used')}"
            )
            
            # Parse JSON if json_mode is enabled
            if json_mode and response_content:
                try:
                    print("🔍 DEBUG: Parsing JSON response...")
                    response_content = json.loads(response_content)
                    print(f"🔍 DEBUG: Parsed JSON response type: {type(response_content)}")
                    print(f"🔍 DEBUG: Parsed JSON keys: {list(response_content.keys()) if isinstance(response_content, dict) else 'Not a dict'}")
                    
                    if serializer:
                        # Add validation data if provided
                        if serializer_validation_data and isinstance(response_content, dict):
                            response_content.update(serializer_validation_data)
                        
                        # Validate with serializer if provided
                        print("🔍 DEBUG: Validating with serializer...")
                        serializer_instance = serializer(data=response_content)
                        serializer_instance.is_valid(raise_exception=True)
                        response_content = serializer_instance.validated_data
                        print("🔍 DEBUG: Serializer validation passed")
                        
                except Exception as e:
                    print(
                        f"AI LP Gen: JSON response validation failed: {e}\n\nResponse: {response_content}"
                    )
                    raise Exception(
                        f"JSON response validation failed: {e}\n\nResponse: {response_content}"
                    )
            
            print(f"🔍 DEBUG: Final response_content: {response_content}")
            return response_content, tokens_used
            
        except Exception as e:
            print(f"OpenAI API call failed: {e}")
            raise e

    @classmethod
    def generate_rubric_from_lesson_plan(
        cls,
        lesson_plan: str,
        api_key: Optional[str] = None,
        model: str = "gpt-4o"
    ) -> Tuple[Dict[str, Any], Dict[str, int]]:
        """
        Generate rubric from lesson plan using single prompt approach
        """
        print(f"🔍 DEBUG: generate_rubric_from_lesson_plan called with lesson plan length: {len(lesson_plan)}")
        
        # Format the prompt with the lesson plan
        print("🔍 DEBUG: Formatting prompt template...")
        prompt = SINGLE_PROMPT_TEMPLATE.format(lesson_plan=lesson_plan)
        print(f"🔍 DEBUG: Prompt length: {len(prompt)}")
        print(f"🔍 DEBUG: Prompt preview: {prompt[:500]}...")
        
        # Call the completion method
        print("🔍 DEBUG: Calling get_completion...")
        response_content, tokens_used = cls.get_completion(
            api_key=api_key,
            prompt=prompt,
            model=model,
            json_mode=True,
            max_tokens=4000
        )
        
        print(f"🔍 DEBUG: get_completion returned response type: {type(response_content)}")
        print(f"🔍 DEBUG: Response content: {response_content}")
        
        return response_content, tokens_used 