> ## Documentation Index
> Fetch the complete documentation index at: https://platform.minimaxi.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# 文本对话

> 使用本接口调用 M2-her 模型，支持角色扮演、多轮对话等对话场景。支持丰富的角色设定（system、user_system、group 等）和示例对话学习。



## OpenAPI

````yaml api-reference/text/api/openapi-chat.json post /v1/text/chatcompletion_v2
openapi: 3.1.0
info:
  title: MiniMax Text API
  description: >-
    MiniMax text generation API with support for chat completion and streaming
    output
  license:
    name: MIT
  version: 1.0.0
servers:
  - url: https://api.minimaxi.com
security:
  - bearerAuth: []
paths:
  /v1/text/chatcompletion_v2:
    post:
      tags:
        - Text Generation
      summary: Text Generation V2
      operationId: chatCompletionV2
      parameters:
        - name: Content-Type
          in: header
          required: true
          description: 请求体的媒介类型，请设置为 `application/json`，确保请求数据的格式为 JSON
          schema:
            type: string
            enum:
              - application/json
            default: application/json
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ChatCompletionReq'
            examples:
              Request:
                value:
                  model: M2-her
                  messages:
                    - role: system
                      name: MiniMax AI
                    - role: user
                      name: 用户
                      content: 你好
              Stream:
                value:
                  model: M2-her
                  messages:
                    - role: system
                      name: MiniMax AI
                    - role: user
                      name: 用户
                      content: 你好
                  stream: true
        required: true
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ChatCompletionResp'
              examples:
                Request:
                  value:
                    id: 05b81ca0cde9e60c3ae4ce7f60103250
                    choices:
                      - finish_reason: stop
                        index: 0
                        message:
                          content: 你好！我是 M2-her，由 MiniMax 开发的人工智能助手。很高兴认识你！有什么我可以帮忙的吗？
                          role: assistant
                          name: MiniMax AI
                          audio_content: ''
                    created: 1768483232
                    model: M2-her
                    object: chat.completion
                    usage:
                      total_tokens: 199
                      total_characters: 0
                      prompt_tokens: 176
                      completion_tokens: 23
                    input_sensitive: false
                    output_sensitive: false
                    input_sensitive_type: 0
                    output_sensitive_type: 0
                    output_sensitive_int: 0
                    base_resp:
                      status_code: 0
                      status_msg: ''
                Stream:
                  value:
                    - id: 02ff7eb7fe6fb505b9d5cb6945a1a98b
                      choices:
                        - index: 0
                          delta:
                            content: 你好
                            role: assistant
                      created: 1722829751
                      model: M2-her
                      object: chat.completion.chunk
                      output_sensitive: false
                      input_sensitive_type: 0
                      output_sensitive_type: 0
                    - id: 02ff7eb7fe6fb505b9d5cb6945a1a98b
                      choices:
                        - finish_reason: stop
                          index: 0
                          delta:
                            content: ！有什么可以帮助你的吗？
                            role: assistant
                      created: 1722829751
                      model: M2-her
                      object: chat.completion.chunk
                      output_sensitive: false
                      input_sensitive_type: 0
                      output_sensitive_type: 0
                    - id: 02ff7eb7fe6fb505b9d5cb6945a1a98b
                      choices:
                        - finish_reason: stop
                          index: 0
                          message:
                            content: 你好！有什么可以帮助你的吗？
                            role: assistant
                      created: 1722829751
                      model: M2-her
                      object: chat.completion
                      usage:
                        total_tokens: 73
                      input_sensitive: false
                      output_sensitive: false
                      input_sensitive_type: 0
                      output_sensitive_type: 0
                      base_resp:
                        status_code: 0
                        status_msg: ''
            text/event-stream:
              schema:
                $ref: '#/components/schemas/ChatCompletionResp'
              examples:
                Stream:
                  value:
                    - id: 02ff7eb7fe6fb505b9d5cb6945a1a98b
                      choices:
                        - index: 0
                          delta:
                            content: 你好
                            role: assistant
                      created: 1722829751
                      model: M2-her
                      object: chat.completion.chunk
                      output_sensitive: false
                      input_sensitive_type: 0
                      output_sensitive_type: 0
                    - id: 02ff7eb7fe6fb505b9d5cb6945a1a98b
                      choices:
                        - finish_reason: stop
                          index: 0
                          delta:
                            content: ！有什么可以帮助你的吗？
                            role: assistant
                      created: 1722829751
                      model: M2-her
                      object: chat.completion.chunk
                      output_sensitive: false
                      input_sensitive_type: 0
                      output_sensitive_type: 0
                    - id: 02ff7eb7fe6fb505b9d5cb6945a1a98b
                      choices:
                        - finish_reason: stop
                          index: 0
                          message:
                            content: 你好！有什么可以帮助你的吗？
                            role: assistant
                      created: 1722829751
                      model: M2-her
                      object: chat.completion
                      usage:
                        total_tokens: 73
                      input_sensitive: false
                      output_sensitive: false
                      input_sensitive_type: 0
                      output_sensitive_type: 0
                      base_resp:
                        status_code: 0
                        status_msg: ''
components:
  schemas:
    ChatCompletionReq:
      type: object
      required:
        - model
        - messages
      properties:
        model:
          type: string
          description: 模型 ID。可选值：`M2-her`
          enum:
            - M2-her
        stream:
          type: boolean
          description: 是否使用流式传输，默认为 `false`。设置为 `true` 后，响应将分批返回
          default: false
        max_completion_tokens:
          type: integer
          format: int64
          description: >-
            指定生成内容长度的上限（Token 数），上限为 2048。超过上限的内容会被截断。如果生成因 `length`
            原因中断，请尝试调高此值。
          minimum: 1
        temperature:
          type: number
          format: double
          description: 温度系数，影响输出随机性，取值范围 (0, 1]，`M2-her` 模型默认值为 1.0。值越高，输出越随机；值越低，输出越确定
          minimum: 0
          exclusiveMinimum: 0
          maximum: 1
          default: 1
        top_p:
          type: number
          format: double
          description: 采样策略，影响输出随机性，取值范围 (0, 1]，`M2-her` 模型默认值为 0.95
          minimum: 0
          exclusiveMinimum: 0
          maximum: 1
          default: 0.95
        messages:
          type: array
          description: 包含对话历史的消息列表。更多 message 参数说明请参考 [文本对话使用指南](/guides/text-chat)
          items:
            $ref: '#/components/schemas/Message'
    ChatCompletionResp:
      type: object
      properties:
        id:
          type: string
          description: 本次响应的唯一 ID
        choices:
          type: array
          description: 响应选择列表
          items:
            type: object
            properties:
              finish_reason:
                type: string
                description: >-
                  生成停止的原因：`stop` (自然结束), `length` (达到 `max_completion_tokens`
                  上限)
                enum:
                  - stop
                  - length
              index:
                type: integer
                description: 选项的索引，从 0 开始
              message:
                type: object
                description: 模型生成的完整回复
                required:
                  - content
                  - role
                properties:
                  content:
                    type: string
                    description: 文本回复内容
                  role:
                    type: string
                    description: 角色，固定为 `assistant`
                    enum:
                      - assistant
        created:
          type: integer
          format: int64
          description: 响应创建的 Unix 时间戳（秒）
        model:
          type: string
          description: 本次请求使用的模型 ID
        object:
          type: string
          description: 对象类型。非流式为 `chat.completion`，流式为 `chat.completion.chunk`
          enum:
            - chat.completion
            - chat.completion.chunk
        usage:
          $ref: '#/components/schemas/Usage'
        input_sensitive:
          type: boolean
          description: 输入内容是否命中敏感词。如果输入内容严重违规，接口会返回内容违规错误信息，回复内容为空
        input_sensitive_type:
          type: integer
          format: int64
          description: >-
            输入命中敏感词类型，当input_sensitive为true时返回。取值为以下其一：1 严重违规；2 色情；3 广告；4 违禁；5
            谩骂；6 暴恐；7 其他
        output_sensitive:
          type: boolean
          description: 输出内容是否命中敏感词。如果输出内容严重违规，接口会返回内容违规错误信息，回复内容为空
        output_sensitive_type:
          type: integer
          format: int64
          description: 输出命中敏感词类型
        base_resp:
          type: object
          description: 错误状态码和详情
          properties:
            status_code:
              type: integer
              format: int64
              description: |-
                状态码

                - `1000`: 未知错误
                - `1001`: 请求超时
                - `1002`: 触发限流
                - `1004`: 鉴权失败
                - `1008`: 余额不足
                - `1013`: 服务内部错误
                - `1027`: 输出内容错误
                - `1039`:  Token 超出限制
                - `2013`: 参数错误

                更多内容可查看 [错误码查询列表](/api-reference/errorcode) 了解详情
            status_msg:
              type: string
              description: 错误详情
    Message:
      type: object
      required:
        - role
        - content
      properties:
        role:
          type: string
          enum:
            - system
            - user
            - assistant
            - user_system
            - group
            - sample_message_user
            - sample_message_ai
          description: |-
            消息发送者的角色
            - `system`: 设定模型的角色和行为
            - `user`: 用户的输入
            - `assistant`: 模型的历史回复
            - `user_system`: 设定用户的角色和人设
            - `group`: 对话的名称
            - `sample_message_user`: 示例的用户输入
            - `sample_message_ai`: 示例的模型输出
        name:
          type: string
          description: 发送者的名称。若同一类型的角色有多个，须提供具体名称以区分
        content:
          type: string
          description: 消息内容
    Usage:
      type: object
      description: 本次请求的 Token 使用情况统计
      properties:
        total_tokens:
          type: integer
          description: 消耗的总 Token 数
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
      description: |-
        `HTTP: Bearer Auth`
         - Security Scheme Type: http
         - HTTP Authorization Scheme: Bearer API_key，用于验证账户信息，可在 [账户管理>接口密钥](https://platform.minimaxi.com/user-center/basic-information/interface-key) 中查看。

````