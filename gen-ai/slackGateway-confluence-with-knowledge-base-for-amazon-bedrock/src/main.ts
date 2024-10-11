// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { App, DefaultStackSynthesizer } from "aws-cdk-lib";
import { SlackBotStack } from "./stack";

const app = new App();

new SlackBotStack(app, "slack-bedrock-integration", {
	synthesizer: new DefaultStackSynthesizer({
		generateBootstrapVersionRule: false,
	}),
	stackName: process.env.STACK_NAME ?? "slack-bedrock-integration",
});

app.synth();
