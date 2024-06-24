## AWS Korea Startup Samples

Welcome. This reference has been prepared by Startup Solution Architects at AWS Korea to help Startups easily find additional resources that provide sample codes or workshops.

We hope this proves useful as you navigate the various options available to you for maximizing the value you can get out of running on AWS. As always, should you have questions on anything, please don't hesitate to contact your local startup team. If you aren't already in contact with them, simply visit [https://www.awsstartup.io/](https://www.awsstartup.io/) and click on the [**MEET THE EXPERT for STARTUP**](https://pages.awscloud.com/office-hour-startup.html) button.

## Getting specific source directories

This repository has so many files that it is a `monorepo`.
So if you want to get a specific source directory, you better use the `git sparse-chekcout` command like this.

For example, suppose you want to clone the `rag-with-amazon-bedrock-and-opensearch` project.

Run the following command from your terminal.

   ```
   git clone https://github.com/aws-kr-startup-samples.git
   cd aws-kr-startup-samples
   git sparse-checkout init --cone
   git sparse-checkout set gen-ai/rag-with-amazon-bedrock-and-opensearch
   ```

:information_source: For more information about `git sparse-checkout`, see [this article](https://github.blog/2020-01-17-bring-your-monorepo-down-to-size-with-sparse-checkout/).

## Resources

 * [AWS Startup](https://www.awsstartup.io/): AWS를 시작하는데 필요한 AWS 핵심 서비스의 특장점과 실제 활용 사례를 소개
 * [AWS Startup Bootcamp](https://www.awsbootcamp.io/): AWS에 익숙하지 않은 Startup 개발자 분들이, 보다 빠르게 AWS 위에서의 개발을 이해하고 개발을 시작하실 수 있게 보다 실용적인 내용을 소개

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
